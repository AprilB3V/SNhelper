from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import snhelper.web_api as web_api
from snhelper.web_api import create_app


def test_fastapi_crud_and_chat(monkeypatch):
    monkeypatch.setenv("SNHELPER_API_KEY", "test-key")
    path = Path("data") / f"test-web-{uuid4().hex}.db"
    app = create_app(str(path))
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-key"}

    health = client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert client.get("/health").status_code == 401

    project = client.post("/projects", json={"name": "测试项目"}, headers=headers)
    assert project.status_code == 200
    project_id = project.json()["id"]
    assert any(item["id"] == project_id for item in client.get("/projects", headers=headers).json())

    task = client.post("/tasks", json={"title": "验证 FastAPI 调用", "duration": 15, "project": project_id}, headers=headers)
    assert task.status_code == 200
    task_id = task.json()["id"]
    updated = client.patch(f"/tasks/{task_id}", json={"title": "已更新任务"}, headers=headers)
    assert updated.json()["title"] == "已更新任务"
    assert client.post(f"/tasks/{task_id}/complete", headers=headers).json()["success"] is True

    capture = client.post("/capture", json={"content": "保存一个 FastAPI 记忆", "tags": ["后端"]}, headers=headers)
    assert capture.status_code == 200
    capture_id = capture.json()["id"]
    assert client.get("/captures", headers=headers).json()[0]["id"] == capture_id
    assert client.get("/search?q=FastAPI", headers=headers).json()
    memory_chat = client.post("/chat", json={"message": "请回顾 FastAPI 记忆", "project": "测试项目"}, headers=headers)
    assert memory_chat.status_code == 200
    assert "已参考" in memory_chat.json()["message"]
    memory_stream = client.post("/chat?stream=true", json={"message": "请回顾 FastAPI 记忆", "project": "测试项目"}, headers=headers)
    assert memory_stream.status_code == 200
    assert "已参考" in memory_stream.text

    chat = client.post("/chat", json={"message": "请拆解一个任务", "project": "测试项目"}, headers=headers)
    assert chat.status_code == 200
    assert "message" in chat.json()
    assert chat.json()["results"]

    stream = client.post("/chat?stream=true", json={"message": "请开始执行", "project": "测试项目"}, headers=headers)
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers["content-type"]
    assert "[DONE]" in stream.text
    event_lines = [line.removeprefix("data: ").strip() for line in stream.text.splitlines() if line.startswith("data:")]
    assert any(json.loads(line).get("agent") for line in event_lines if line != "[DONE]")
    app.state.store.close()
    app.state.memory.close()
    path.unlink(missing_ok=True)


def test_external_openai_compatible_provider(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "连接成功"}}]}).encode()

    monkeypatch.setattr(web_api.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    app = create_app(f"data/test-provider-{uuid4().hex}.db")
    client = TestClient(app)
    config = {"base_url": "https://provider.example/v1", "api_key": "provider-key", "model": "demo-chat"}
    tested = client.post("/provider/test", json=config)
    assert tested.status_code == 200
    assert tested.json()["success"] is True
    chat = client.post("/chat", json={"message": "测试外部模型", "project": "测试", "model_base_url": config["base_url"], "model_api_key": config["api_key"], "model_name": config["model"]})
    assert chat.status_code == 200
    assert chat.json()["message"] == "连接成功"
    app.state.store.close()
    app.state.memory.close()
    Path(app.state.store.path).unlink(missing_ok=True)
