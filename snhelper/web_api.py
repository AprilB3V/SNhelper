from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from .memory import SQLiteMemoryStore
from .models import Memory
from .orchestrator import Orchestrator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> str:
    configured = os.getenv("SNHELPER_DB_PATH", "data/snhelper.db")
    return str(Path(configured))


def _row_project(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "name": row["name"], "color": row["color"]}


def _row_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
        "duration": int(row["duration"]),
        "project": row["project"],
        "date": row["task_date"],
    }


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: str | None = None


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    duration: int = Field(default=15, ge=15, le=480)
    project: str | None = None
    date: str | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    duration: int | None = Field(default=None, ge=15, le=480)
    project: str | None = None
    done: bool | None = None


class CaptureInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    tags: list[str] = Field(default_factory=list)


class TagSuggestionInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    agent: str = "Archivist"


class ChatInput(BaseModel):
    model_config = {"protected_namespaces": ()}
    message: str = Field(min_length=1, max_length=20000)
    project: str = "全部项目"
    memory_context: list[dict[str, Any]] = Field(default_factory=list, max_length=5)
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_name: str | None = None


class ProviderConfig(BaseModel):
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)
    model: str = Field(default="gpt-4o-mini", min_length=1, max_length=200)


class MemoryPatch(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    tags: list[str] = Field(default_factory=list)


class WebStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or _db_path()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '#d2a55e'
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                duration INTEGER NOT NULL DEFAULT 15,
                project TEXT,
                task_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS captures (
                id TEXT PRIMARY KEY,
                memory_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            """
        )
        self.db.execute(
            "INSERT OR IGNORE INTO projects(id, name, color) VALUES ('all', '全部项目', '#d2a55e')"
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()


def create_app(db_path: str | None = None) -> FastAPI:
    store = WebStore(db_path)
    memory = SQLiteMemoryStore(db_path or _db_path())
    orchestrator = Orchestrator(memory)
    app = FastAPI(title="SNhelper Agent API", version="0.1.0")
    app.state.store = store
    app.state.memory = memory
    app.state.orchestrator = orchestrator

    origins = os.getenv("SNHELPER_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item.strip() for item in origins.split(",") if item.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def auth(authorization: str | None = Header(default=None)) -> None:
        expected = os.getenv("SNHELPER_API_KEY", "").strip()
        if not expected:
            return
        if authorization != f"Bearer {expected}":
            raise HTTPException(status_code=401, detail="无效的 API Key")

    def provider_url(base_url: str) -> str:
        url = base_url.strip().rstrip("/")
        return url if url.endswith("/chat/completions") else f"{url}/chat/completions"

    def call_provider(config: ProviderConfig, message: str, project: str) -> str:
        body = json.dumps({
            "model": config.model,
            "messages": [
                {"role": "system", "content": "你是个人认知外骨骼的总调度器。请用中文回答，给出清晰、可执行的建议。"},
                {"role": "user", "content": f"当前项目：{project}\n{message}"},
            ],
            "temperature": 0.2,
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(provider_url(config.base_url), data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.api_key}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise HTTPException(status_code=502, detail=f"模型服务返回 {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise HTTPException(status_code=502, detail=f"无法连接模型服务：{exc}") from exc
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="模型服务响应缺少 choices[0].message.content") from exc

    def project_or_404(project_id: str) -> sqlite3.Row:
        row = store.db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        return row

    def task_or_404(task_id: str) -> sqlite3.Row:
        row = store.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return row

    @app.get("/health", dependencies=[Depends(auth)])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "agents": [
                {"id": "orchestrator", "name": "Orchestrator", "role": "总调度器", "color": "#d2a55e"},
                {"id": "archivist", "name": "Archivist", "role": "知识库管家", "color": "#72c6c5"},
                {"id": "enforcer", "name": "Enforcer", "role": "执行督导", "color": "#f0806b"},
                {"id": "strategist", "name": "Strategist", "role": "战略参谋", "color": "#a9b7f0"},
                {"id": "simulator", "name": "Simulator", "role": "社交沙盘", "color": "#d19ce3"},
            ],
        }

    @app.get("/projects", dependencies=[Depends(auth)])
    def list_projects() -> list[dict[str, Any]]:
        rows = store.db.execute("SELECT * FROM projects ORDER BY id = 'all' DESC, name").fetchall()
        return [_row_project(row) for row in rows]

    @app.post("/projects", dependencies=[Depends(auth)])
    def create_project(payload: ProjectInput) -> dict[str, Any]:
        project_id = f"project-{int(datetime.now().timestamp() * 1000)}"
        try:
            store.db.execute("INSERT INTO projects(id, name, color) VALUES (?, ?, ?)", (project_id, payload.name.strip(), payload.color or "#d2a55e"))
            store.db.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="项目名称已存在") from exc
        return _row_project(project_or_404(project_id))

    @app.patch("/projects/{project_id}", dependencies=[Depends(auth)])
    def update_project(project_id: str, payload: ProjectInput) -> dict[str, Any]:
        project_or_404(project_id)
        if project_id == "all":
            raise HTTPException(status_code=400, detail="不能修改全部项目")
        try:
            store.db.execute("UPDATE projects SET name = ?, color = COALESCE(?, color) WHERE id = ?", (payload.name.strip(), payload.color, project_id))
            store.db.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="项目名称已存在") from exc
        return _row_project(project_or_404(project_id))

    @app.delete("/projects/{project_id}", status_code=204, dependencies=[Depends(auth)])
    def delete_project(project_id: str) -> Response:
        project_or_404(project_id)
        if project_id == "all":
            raise HTTPException(status_code=400, detail="不能删除全部项目")
        store.db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        store.db.execute("UPDATE tasks SET project = NULL WHERE project = ?", (project_id,))
        store.db.commit()
        return Response(status_code=204)

    @app.get("/tasks", dependencies=[Depends(auth)])
    def list_tasks(task_date: str | None = Query(default=None, alias="date")) -> list[dict[str, Any]]:
        target = task_date or date.today().isoformat()
        rows = store.db.execute("SELECT * FROM tasks WHERE task_date = ? ORDER BY done, id DESC", (target,)).fetchall()
        return [_row_task(row) for row in rows]

    @app.post("/tasks", dependencies=[Depends(auth)])
    def create_task(payload: TaskInput) -> dict[str, Any]:
        task_id = f"task-{int(datetime.now().timestamp() * 1000)}"
        task_date = payload.date or date.today().isoformat()
        store.db.execute("INSERT INTO tasks(id, title, duration, project, task_date) VALUES (?, ?, ?, ?, ?)", (task_id, payload.title.strip(), payload.duration, payload.project, task_date))
        store.db.commit()
        return _row_task(task_or_404(task_id))

    @app.patch("/tasks/{task_id}", dependencies=[Depends(auth)])
    def update_task(task_id: str, payload: TaskPatch) -> dict[str, Any]:
        task_or_404(task_id)
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return _row_task(task_or_404(task_id))
        columns = {"title": "title", "duration": "duration", "project": "project", "done": "done"}
        assignments = [f"{columns[key]} = ?" for key in values if key in columns]
        params = [int(value) if key == "done" else value for key, value in values.items() if key in columns]
        if assignments:
            store.db.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", [*params, task_id])
            store.db.commit()
        return _row_task(task_or_404(task_id))

    @app.delete("/tasks/{task_id}", status_code=204, dependencies=[Depends(auth)])
    def delete_task(task_id: str) -> Response:
        task_or_404(task_id)
        store.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        store.db.commit()
        return Response(status_code=204)

    @app.post("/tasks/{task_id}/complete", dependencies=[Depends(auth)])
    def complete_task(task_id: str) -> dict[str, Any]:
        row = task_or_404(task_id)
        store.db.execute("UPDATE tasks SET done = ? WHERE id = ?", (0 if row["done"] else 1, task_id))
        store.db.commit()
        return {"success": True}

    @app.post("/capture", dependencies=[Depends(auth)])
    def create_capture(payload: CaptureInput) -> dict[str, Any]:
        cleaned_tags = list(dict.fromkeys(tag.strip() for tag in payload.tags if tag.strip()))
        memory_item = memory.add(Memory(title=payload.content.strip().replace("\n", " ")[:80], content=payload.content.strip(), tags=cleaned_tags))
        capture_id = f"c-{memory_item.memory_id}"
        store.db.execute("INSERT INTO captures(id, memory_id, content, tags, created_at) VALUES (?, ?, ?, ?, ?)", (capture_id, memory_item.memory_id, memory_item.content, json.dumps(memory_item.tags, ensure_ascii=False), memory_item.created_at))
        store.db.commit()
        return {"success": True, "id": capture_id}

    @app.get("/captures", dependencies=[Depends(auth)])
    def list_captures() -> list[dict[str, Any]]:
        rows = store.db.execute("SELECT * FROM captures ORDER BY created_at DESC").fetchall()
        return [{"id": row["id"], "content": row["content"], "tags": json.loads(row["tags"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]} for row in rows]

    @app.patch("/captures/{capture_id}", dependencies=[Depends(auth)])
    def update_capture(capture_id: str, payload: CaptureInput) -> dict[str, Any]:
        row = store.db.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="速记不存在")
        tags = list(dict.fromkeys(tag.strip() for tag in payload.tags if tag.strip()))
        store.db.execute("UPDATE captures SET content = ?, tags = ?, updated_at = ? WHERE id = ?", (payload.content.strip(), json.dumps(tags, ensure_ascii=False), _now(), capture_id))
        store.db.execute("UPDATE memories SET content = ?, title = ?, tags = ? WHERE id = ?", (payload.content.strip(), payload.content.strip().replace("\n", " ")[:80], ",".join(tags), row["memory_id"]))
        store.db.commit()
        updated = store.db.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
        return {"id": updated["id"], "content": updated["content"], "tags": json.loads(updated["tags"]), "createdAt": updated["created_at"], "updatedAt": updated["updated_at"]}

    @app.delete("/captures/{capture_id}", status_code=204, dependencies=[Depends(auth)])
    def delete_capture(capture_id: str) -> Response:
        row = store.db.execute("SELECT memory_id FROM captures WHERE id = ?", (capture_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="速记不存在")
        store.db.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
        store.db.execute("DELETE FROM memories WHERE id = ?", (row["memory_id"],))
        store.db.commit()
        return Response(status_code=204)

    @app.post("/capture/suggest-tags", dependencies=[Depends(auth)])
    def suggest_tags(payload: TagSuggestionInput) -> list[str]:
        rules = {"Archivist": ["知识库", "归档"], "Strategist": ["战略", "决策"], "Enforcer": ["执行", "任务"], "Simulator": ["社交", "沟通"]}
        common = [word for word in ("创业", "产品", "考研", "论文", "复盘", "灵感", "计划", "任务", "沟通", "会议") if word in payload.content]
        return list(dict.fromkeys([*rules.get(payload.agent, ["灵感"]), *common]))[:5]

    @app.post("/provider/test", dependencies=[Depends(auth)])
    def test_provider(payload: ProviderConfig) -> dict[str, Any]:
        content = call_provider(payload, "只回复：连接成功", "连接测试")
        return {"success": True, "model": payload.model, "message": content}

    @app.get("/search", dependencies=[Depends(auth)])
    def search(query: str = Query(default="", alias="q")) -> list[dict[str, Any]]:
        memories = memory.recent(100) if not query.strip() else memory.search(query, 100)
        return [{"id": str(item.memory_id), "content": item.content, "tags": item.tags, "score": 1.0 if not query else 0.8, "createdAt": item.created_at} for item in memories]

    @app.patch("/memories/{memory_id}", dependencies=[Depends(auth)])
    def update_memory(memory_id: int, payload: MemoryPatch) -> dict[str, Any]:
        row = memory._db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="记忆不存在")
        tags = list(dict.fromkeys(tag.strip() for tag in payload.tags if tag.strip()))
        memory._db.execute("UPDATE memories SET content = ?, title = ?, tags = ? WHERE id = ?", (payload.content.strip(), payload.content.strip().replace("\n", " ")[:80], ",".join(tags), memory_id))
        memory._db.commit()
        return {"id": str(memory_id), "content": payload.content.strip(), "tags": tags, "score": 1.0, "createdAt": row["created_at"]}

    @app.delete("/memories/{memory_id}", status_code=204, dependencies=[Depends(auth)])
    def delete_memory(memory_id: int) -> Response:
        cursor = memory._db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="记忆不存在")
        memory._db.commit()
        return Response(status_code=204)

    def orchestration_payload(payload: ChatInput) -> tuple[str, list[dict[str, Any]], Any]:
        context = payload.memory_context[:5]
        if not context:
            context = [{"id": str(item.memory_id), "content": item.content, "tags": item.tags, "score": 1.0} for item in memory.search(payload.message, 5)]
        memory_note = ""
        if context:
            memory_note = "相关灵感速记（仅作参考，请结合当前问题判断）：\n" + "\n".join(f"- {item.get('content', '')}（标签：{', '.join(item.get('tags', []))}）" for item in context)
        if payload.model_base_url and payload.model_api_key:
            content = call_provider(
                ProviderConfig(base_url=payload.model_base_url, api_key=payload.model_api_key, model=payload.model_name or "gpt-4o-mini"),
                f"{memory_note}\n\n{payload.message}" if memory_note else payload.message,
                payload.project,
            )
            result = orchestrator.handle(payload.message)
            prefix = f"已参考 {len(context)} 条灵感速记。\n\n" if context else ""
            return prefix + content, [{"agent": "Orchestrator", "summary": "外部模型回答", "content": prefix + content, "data": {"memory_ids": [item.get("id") for item in context]}, "follow_up": []}], result
        result = orchestrator.handle(f"项目：{payload.project}\n{memory_note}\n\n{payload.message}")
        results = [{"agent": item.agent.title(), "summary": item.summary, "content": item.content, "data": item.data, "follow_up": item.follow_up} for item in result.results]
        if memory_note and results:
            results[0]["content"] = f"已参考 {len(context)} 条灵感速记：\n{memory_note}\n\n{results[0]['content']}"
        content = "\n\n".join(f"[{item['agent']}]\n{item['content']}" for item in results)
        return content, results, result

    @app.post("/chat", dependencies=[Depends(auth)])
    async def chat(payload: ChatInput, request: Request, stream: bool = Query(default=False)) -> Any:
        content, results, result = orchestration_payload(payload)
        if not stream:
            return {"message": content, "content": content, "agent": results[-1]["agent"] if results else "Orchestrator", "route": {"primary": result.route.primary.value, "secondary": [item.value for item in result.route.secondary], "confidence": result.route.confidence}, "results": results}

        async def events() -> AsyncIterator[str]:
            for item in results:
                if await request.is_disconnected():
                    break
                text = item["content"]
                yield f"data: {json.dumps({'agent': item['agent'], 'delta': text}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
