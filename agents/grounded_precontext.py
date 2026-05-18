"""Phase 3.1: Gemini-native grounded precontext agent.

Optional. Gated by ``GEMINI_GROUNDING_ENABLED``. The planner can call this
agent in parallel with the usual DDG/arXiv precontext search; output lives on
``PlannerPrecontext.grounded_precontext``.
"""

from __future__ import annotations

from backend.models import GroundedPrecontext
from backend.providers.llm.gemini_grounding import GeminiGroundingProvider


class GroundedPrecontextAgent:
    """Runs one Gemini Search-grounded call and returns a typed precontext block."""

    def __init__(self, provider: GeminiGroundingProvider | None = None):
        self.provider = provider or GeminiGroundingProvider()

    async def run(self, user_query: str) -> GroundedPrecontext:
        return await self.provider.to_precontext(user_query)
