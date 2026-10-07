from __future__ import annotations

from ..models import AgentResult
from .base import Agent


class Simulator(Agent):
    name = "simulator"

    def handle(self, text: str) -> AgentResult:
        model_risk = self.model_text(
            "你是社交沙盘推演师。指出该场景中最可能的沟通风险，限 30 字。",
            text,
        )
        content = (
            f"场景：{text.strip()}\n\n"
            + (f"主要风险：{model_risk}\n" if model_risk else "")
            + "对方可能的真实目标：获取信息、降低风险、维护边界。\n"
            + "你的开场：我想先确认目标和约束，再给出一个具体方案。\n"
            + "若被质疑：你说得对，我先把可验证的事实和假设分开。\n"
            + "若被拒绝：我尊重这个选择；为了避免误解，我补充最后一个关键事实。\n"
            + "若情绪升高：我们先暂停结论，只确认各自需要什么。"
        )
        return AgentResult(
            agent=self.name,
            summary="已生成社交沙盘和应急话术卡",
            content=content,
            data={"role_cards": ["求证", "被质疑", "被拒绝", "冲突升级"]},
        )
