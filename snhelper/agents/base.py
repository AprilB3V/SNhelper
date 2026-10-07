from __future__ import annotations

from abc import ABC, abstractmethod

from ..llm import ModelBridge
from ..models import AgentResult


class Agent(ABC):
    name: str

    def __init__(self, model: ModelBridge | None = None) -> None:
        self.model = model if isinstance(model, ModelBridge) else ModelBridge(model)

    def model_text(self, system: str, user: str) -> str | None:
        return self.model.invoke_text(system, user)

    @abstractmethod
    def handle(self, text: str) -> AgentResult:
        raise NotImplementedError
