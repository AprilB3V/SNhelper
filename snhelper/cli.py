from __future__ import annotations

import argparse
import json
import os

from .llm import build_openai_bridge
from .orchestrator import Orchestrator


def _format(result) -> str:
    lines = [f"路由：{result.route.primary.value}（置信度 {result.route.confidence:.2f}）"]
    if result.route.secondary:
        lines.append("协同：" + ", ".join(intent.value for intent in result.route.secondary))
    lines.append(result.route.rationale)
    for agent_result in result.results:
        lines.append(f"\n[{agent_result.agent}] {agent_result.summary}\n{agent_result.content}")
        lines.extend(f"下一步：{item}" for item in agent_result.follow_up)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="SNhelper personal cognitive exoskeleton")
    subparsers = parser.add_subparsers(dest="command")
    ask = subparsers.add_parser("ask", help="route an input through the agent system")
    ask.add_argument("text", nargs="?", help="input text; omit for interactive mode")
    ask.add_argument("--llm", action="store_true", help="use ChatOpenAI when configured")
    search = subparsers.add_parser("search", help="search archived thoughts")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.command is None:
        args.command = "ask"
        args.text = None

    model = None
    if getattr(args, "llm", False):
        model = build_openai_bridge().model
    orchestrator = Orchestrator(model=model)
    if args.command == "search":
        result = orchestrator.search_memory(args.query, args.limit)
        print(result.content)
        return
    text = args.text or input("输入：").strip()
    if not text:
        raise SystemExit("输入不能为空")
    print(_format(orchestrator.handle(text)))


if __name__ == "__main__":
    main()

