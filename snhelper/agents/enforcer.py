from __future__ import annotations

import re

from ..models import AgentResult, TaskStep
from .base import Agent


class Enforcer(Agent):
    name = "enforcer"

    def handle(self, text: str) -> AgentResult:
        goal = text.strip().rstrip("。.!！") or "当前目标"
        steps = [
            TaskStep(1, f"打开完成“{goal}”所需的唯一工具或文件", "工具已打开", 2),
            TaskStep(2, "写下完成标准，并把目标缩成一个可交付的小样本", "出现一条可检查的完成标准", 5),
            TaskStep(3, "启动 10 分钟计时，只执行第一个物理动作", "计时结束且留下可见产物", 10),
            TaskStep(4, "记录阻塞点，选择继续、改小或停止实验", "阻塞点被写成下一步动作", 3),
        ]
        content = "\n".join(f"{step.order}. [{step.minutes} 分钟] {step.action}（完成标志：{step.done_when}）" for step in steps)
        model_constraint = self.model_text(
            "你是冷静的执行督导。只指出一个最容易被忽略的现实约束，用一句话表达。",
            goal,
        )
        if model_constraint:
            content += f"\n现实约束：{model_constraint}"
        return AgentResult(
            agent=self.name,
            summary="已将目标压缩成物理动作",
            content=content,
            data={"steps": steps, "experiment_question": f"10 分钟后，{goal}是否产生了可见证据？"},
            follow_up=["现在执行第 1 步。完成前不允许继续设计系统。"],
        )
