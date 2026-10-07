from __future__ import annotations

import re

from ..memory import MemoryStore
from ..models import AgentResult, Memory
from .base import Agent


class Archivist(Agent):
    name = "archivist"

    def __init__(self, store: MemoryStore, model=None) -> None:
        super().__init__(model)
        self.store = store

    def _extract_tags(self, text: str) -> list[str]:
        candidates = re.findall(r"#[\w\u4e00-\u9fff-]+|\b[A-Za-z][A-Za-z0-9_-]{2,}\b", text)
        tags = [item.lstrip("#").lower() for item in candidates]
        if not tags:
            tags = ["未分类"]
        return list(dict.fromkeys(tags[:8]))

    def handle(self, text: str) -> AgentResult:
        title = text.strip().replace("\n", " ")[:48] or "未命名思维碎片"
        tags = self._extract_tags(text)
        memory = self.store.add(Memory(title=title, content=text.strip(), tags=tags))
        model_summary = self.model_text(
            "你是个人知识库管理员。用一句话提炼输入的核心逻辑，不要添加事实。",
            text,
        )
        return AgentResult(
            agent=self.name,
            summary="已归档思维碎片",
            content=f"已保存：{memory.title}" + (f"\n核心逻辑：{model_summary}" if model_summary else ""),
            data={"memory_id": memory.memory_id, "tags": memory.tags},
            follow_up=["继续输入关键词，可从历史思维碎片中模糊检索。"],
        )

    def search(self, query: str, limit: int = 5) -> AgentResult:
        memories = self.store.search(query, limit)
        lines = [f"[{m.memory_id}] {m.title} | {', '.join(m.tags)}\n{m.content}" for m in memories]
        return AgentResult(
            agent=self.name,
            summary=f"找到 {len(memories)} 条相关记忆",
            content="\n\n".join(lines) if lines else "没有找到匹配的思维碎片。",
            data={"memories": memories},
        )
