"""Small LangChain bridge with a deterministic fallback.

The framework does not require a provider at runtime. Any object exposing
LangChain's ``invoke`` method can be passed to the agents when a model is
available. The agents still return useful structured results without it.
"""

from __future__ import annotations

from typing import Any


class ModelBridge:
    def __init__(self, model: Any | None = None) -> None:
        self.model = model

    @property
    def enabled(self) -> bool:
        return self.model is not None and hasattr(self.model, "invoke")

    def invoke_text(self, system: str, user: str) -> str | None:
        if not self.enabled:
            return None
        prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        response = self.model.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(str(item) for item in content)
        return str(content).strip()


def build_openai_bridge(model_name: str = "gpt-4o-mini") -> ModelBridge:
    """Build an optional LangChain OpenAI bridge.

    Imports are intentionally delayed so the no-LLM mode has zero third-party
    requirements. An absent package or API key is reported clearly.
    """

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError("Install snhelper[langchain] to use the OpenAI bridge") from exc
    return ModelBridge(ChatOpenAI(model=model_name, temperature=0.2))

