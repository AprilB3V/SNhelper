from __future__ import annotations

from ..memory import MemoryStore
from ..models import AgentResult
from .base import Agent


class Strategist(Agent):
    name = "strategist"

    def __init__(self, store: MemoryStore, model=None) -> None:
        super().__init__(model)
        self.store = store

    def handle(self, text: str) -> AgentResult:
        memories = self.store.recent(5)
        context = "；".join(memory.title for memory in memories) or "暂无历史记录"
        model_observation = self.model_text(
            "你是战略参谋。针对输入给出一个可验证的长期假设，限 30 字。",
            text,
        ) or "把愿景转成可验证的阶段性假设。"
        content = (
            f"主题：{text.strip()}\n\n"
            f"观察：{model_observation}\n"
            f"近期证据：{context}\n"
            "决策规则：保留能增加自由度和容错率的选项，先做最小实验。\n"
            "本周复盘：事实、偏差、下一次实验，各写一条。"
        )
        return AgentResult(
            agent=self.name,
            summary="已生成战略视角",
            content=content,
            data={"review_questions": ["什么事实改变了我的判断？", "哪个选择提高了长期自由度？", "下一次最小实验是什么？"]},
        )
