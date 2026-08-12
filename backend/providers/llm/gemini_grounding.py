"""Phase 3.1: thin wrapper around Gemini's `googleSearch` grounding tool.

This module is intentionally minimal. It reuses :class:`GeminiProvider`'s
``chat_text`` path (which already forwards a ``tools`` payload) and parses the
``groundingMetadata`` block returned alongside the text. No pipeline agent
depends on this module directly; it is consumed only by
``agents.grounded_precontext.GroundedPrecontextAgent``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.models import GroundedChunk, GroundedPrecontext
from backend.providers.llm.gemini import GeminiProvider


@dataclass
class GroundedResponse:
    text: str
    citations: list[GroundedChunk] = field(default_factory=list)
    rendered_content: str | None = None
    raw_grounding: dict[str, Any] | None = None


class GeminiGroundingProvider:
    """Calls Gemini with the built-in ``googleSearch`` tool enabled."""

    def __init__(self, gemini_provider: GeminiProvider | None = None):
        self.gemini_provider = gemini_provider or GeminiProvider()

    async def chat_grounded(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GroundedResponse:
        response = await self.gemini_provider.chat_text(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=[{"googleSearch": {}}],
        )
        grounding = _grounding_from_raw(response.raw_response or {})
        citations = _citations(grounding)
        rendered = None
        search_entry_point = (grounding or {}).get("searchEntryPoint") or {}
        if isinstance(search_entry_point, dict):
            rendered = search_entry_point.get("renderedContent")
        return GroundedResponse(
            text=response.text,
            citations=citations,
            rendered_content=rendered,
            raw_grounding=grounding,
        )

    async def to_precontext(
        self,
        user_query: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> GroundedPrecontext:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precontext researcher. Use Google Search grounding to collect "
                    "a short factual summary of the user's topic with citations. Do not answer "
                    "the question; just summarize credible background."
                ),
            },
            {"role": "user", "content": user_query},
        ]
        grounded = await self.chat_grounded(messages, temperature=temperature, max_tokens=max_tokens)
        return GroundedPrecontext(
            summary=grounded.text.strip() or "No grounded summary returned.",
            supporting_chunks=grounded.citations,
            rendered_content=grounded.rendered_content,
        )


def _grounding_from_raw(raw: dict[str, Any]) -> dict[str, Any] | None:
    candidates = raw.get("candidates") or []
    if not candidates:
        return None
    return candidates[0].get("groundingMetadata") or None


def _citations(grounding: dict[str, Any] | None) -> list[GroundedChunk]:
    if not grounding:
        return []
    chunks: list[GroundedChunk] = []
    for entry in grounding.get("groundingChunks") or []:
        web = entry.get("web") or {}
        uri = web.get("uri") or web.get("url") or ""
        title = web.get("title") or ""
        snippet = web.get("snippet") or entry.get("segment", {}).get("text", "")
        if not uri:
            continue
        try:
            chunks.append(GroundedChunk(uri=uri, title=title, snippet=snippet))
        except Exception:
            # Gemini occasionally returns non-HTTP URIs (e.g. vertex://). Skip those.
            continue
    return chunks
