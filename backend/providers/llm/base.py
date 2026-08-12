"""LLM provider interface."""

from typing import Protocol

from pydantic import BaseModel

from backend.models import LLMResponse


class LLMProvider(Protocol):
    async def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        ...

    async def chat_json(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        ...
