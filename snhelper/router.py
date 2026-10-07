from __future__ import annotations

import re

from .models import Intent, RouteDecision


class Router:
    """Intent router that supports multi-agent collaboration.

    Keyword scoring is transparent and deterministic. A LangChain model can
    sit above this router later and return the same ``RouteDecision`` schema.
    """

    KEYWORDS: dict[Intent, tuple[str, ...]] = {
        Intent.ARCHIVE: ("记录", "想法", "灵感", "笔记", "记住", "知识", "归档", "搜索", "回忆", "碎片"),
        Intent.EXECUTE: ("做", "执行", "开始", "拖延", "行动", "计划", "任务", "完成", "拆解", "目标"),
        Intent.STRATEGY: ("复盘", "战略", "长期", "愿景", "方向", "选择", "动力", "焦虑", "意义", "创业"),
        Intent.SIMULATE: ("沟通", "社交", "面试", "谈判", "领导", "父母", "同事", "回复", "对方", "冲突"),
    }

    def route(self, text: str) -> RouteDecision:
        normalized = text.lower()
        scores: dict[Intent, int] = {intent: 0 for intent in self.KEYWORDS}
        for intent, words in self.KEYWORDS.items():
            scores[intent] = sum(normalized.count(word.lower()) for word in words)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if ranked[0][1] == 0:
            return RouteDecision(Intent.UNKNOWN, confidence=0.1, rationale="没有匹配到明显意图，默认交给执行拆解。")
        primary, score = ranked[0]
        secondary = [intent for intent, value in ranked[1:] if value > 0 and value >= max(1, score // 2)]
        total = sum(scores.values()) or 1
        confidence = min(0.99, score / total)
        rationale = f"关键词得分：{', '.join(f'{intent.value}={value}' for intent, value in ranked if value)}。"
        return RouteDecision(primary, secondary, confidence, rationale)

