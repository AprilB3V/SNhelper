from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Intent(str, Enum):
    ARCHIVE = "archive"
    EXECUTE = "execute"
    STRATEGY = "strategy"
    SIMULATE = "simulate"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Memory:
    content: str
    title: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = "user"
    memory_id: int | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class TaskStep:
    order: int
    action: str
    done_when: str
    minutes: int = 10


@dataclass(slots=True)
class RouteDecision:
    primary: Intent
    secondary: list[Intent] = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""

    @property
    def intents(self) -> list[Intent]:
        return [self.primary, *self.secondary]


@dataclass(slots=True)
class AgentResult:
    agent: str
    summary: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    follow_up: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OrchestrationResult:
    input_text: str
    route: RouteDecision
    results: list[AgentResult]
    created_at: str = field(default_factory=utc_now)

