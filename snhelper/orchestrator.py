from __future__ import annotations

from .agents import Archivist, Enforcer, Simulator, Strategist
from .memory import MemoryStore, SQLiteMemoryStore
from .models import AgentResult, Intent, OrchestrationResult
from .router import Router


class Orchestrator:
    def __init__(self, store: MemoryStore | None = None, model=None) -> None:
        self.store = store or SQLiteMemoryStore()
        self.router = Router()
        self.agents = {
            Intent.ARCHIVE: Archivist(self.store, model),
            Intent.EXECUTE: Enforcer(model),
            Intent.STRATEGY: Strategist(self.store, model),
            Intent.SIMULATE: Simulator(model),
        }

    def handle(self, text: str) -> OrchestrationResult:
        route = self.router.route(text)
        intents = route.intents
        if route.primary is Intent.UNKNOWN:
            intents = [Intent.EXECUTE]
        results: list[AgentResult] = []
        for intent in intents:
            results.append(self.agents[intent].handle(text))
        return OrchestrationResult(input_text=text, route=route, results=results)

    def search_memory(self, query: str, limit: int = 5) -> AgentResult:
        return self.agents[Intent.ARCHIVE].search(query, limit)

