"""Phase 3.1 tests: Gemini Search grounding wrapper and agent."""

import asyncio
import json

import httpx

from agents.grounded_precontext import GroundedPrecontextAgent
from backend.providers.llm.gemini import GeminiProvider
from backend.providers.llm.gemini_grounding import GeminiGroundingProvider


def _transport_returning_grounding():
    async def handler(request):
        body = json.loads(request.read().decode())
        assert body.get("tools") == [{"googleSearch": {}}]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Grounded summary of Gemini agents."}]},
                        "finishReason": "STOP",
                        "groundingMetadata": {
                            "groundingChunks": [
                                {
                                    "web": {
                                        "uri": "https://ai.google.dev/gemini-api/docs/agents",
                                        "title": "Gemini API: Agents",
                                        "snippet": "Agent overview.",
                                    }
                                },
                                {
                                    "web": {
                                        "uri": "https://ai.google.dev/gemini-api/docs/function-calling",
                                        "title": "Function calling",
                                    }
                                },
                            ],
                            "searchEntryPoint": {"renderedContent": "<div>results</div>"},
                        },
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
            },
        )

    return httpx.MockTransport(handler)


def test_gemini_grounding_provider_parses_chunks():
    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=_transport_returning_grounding())
    grounding = GeminiGroundingProvider(gemini_provider=provider)

    response = asyncio.run(
        grounding.chat_grounded([{"role": "user", "content": "gemini agents"}])
    )

    assert response.text.startswith("Grounded summary")
    assert len(response.citations) == 2
    assert response.citations[0].uri.startswith("https://ai.google.dev/")
    assert response.citations[0].title == "Gemini API: Agents"
    assert response.rendered_content == "<div>results</div>"


def test_grounded_precontext_agent_returns_typed_precontext():
    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=_transport_returning_grounding())
    agent = GroundedPrecontextAgent(provider=GeminiGroundingProvider(gemini_provider=provider))

    precontext = asyncio.run(agent.run("What is the best Gemini agent workflow?"))

    assert precontext.summary.startswith("Grounded summary")
    assert len(precontext.supporting_chunks) == 2
    assert precontext.supporting_chunks[1].uri == "https://ai.google.dev/gemini-api/docs/function-calling"


def test_gemini_grounding_skips_non_http_citations():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "ok"}]},
                        "finishReason": "STOP",
                        "groundingMetadata": {
                            "groundingChunks": [
                                {"web": {"uri": "vertex://internal", "title": "internal"}},
                                {"web": {"uri": "https://example.org/x", "title": "ok"}},
                            ]
                        },
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))
    grounding = GeminiGroundingProvider(gemini_provider=provider)

    response = asyncio.run(grounding.chat_grounded([{"role": "user", "content": "x"}]))

    assert [chunk.uri for chunk in response.citations] == ["https://example.org/x"]




def test_planner_attaches_grounded_precontext_when_flag_enabled(monkeypatch):
    """Phase 3.1 integration: planner should stash grounded precontext on PlannerOutput."""
    import asyncio

    from agents.planner import PlannerAgent
    from backend.models import GroundedChunk, GroundedPrecontext, SearchHeader

    monkeypatch.setattr("agents.planner.config.GEMINI_GROUNDING_ENABLED", True)

    class _StubSearch:
        async def search_web(self, query, max_results):
            return [
                SearchHeader(
                    result_id=f"ddg_{query[:6]}",
                    query=query,
                    title="Real source",
                    url="https://ai.google.dev/gemini-api/docs/agents",
                    snippet="Summary.",
                    rank=1,
                    provider="duckduckgo",
                )
            ]

        async def search_arxiv(self, query, max_results):
            return []

    class _StubLLM:
        async def chat_json(self, messages, schema, **kwargs):
            from backend.models import LLMResponse

            return LLMResponse(
                text="{}",
                parsed_json={
                    "original_query": "Find Gemini agent patterns",
                    "query_type": "technical",
                    "query_interpretation": "Survey Gemini agent patterns.",
                    "precontext_claims": [
                        {
                            "claim": "Agents doc exists.",
                            "source_id": "ddg_Find G",
                            "url": "https://ai.google.dev/gemini-api/docs/agents",
                            "support_level": "weak",
                        },
                        {
                            "claim": "Agents doc exists.",
                            "source_id": "ddg_Find G",
                            "url": "https://ai.google.dev/gemini-api/docs/agents",
                            "support_level": "weak",
                        },
                    ],
                    "research_jobs": [
                        {
                            "job_id": "job_a",
                            "job_name": "a",
                            "objective": "obj a",
                            "search_queries": ["q"],
                            "source_priorities": ["official"],
                            "must_answer": ["x"],
                        },
                        {
                            "job_id": "job_b",
                            "job_name": "b",
                            "objective": "obj b",
                            "search_queries": ["q"],
                            "source_priorities": ["official"],
                            "must_answer": ["x"],
                        },
                    ],
                    "coverage_checklist": ["x"],
                    "planner_confidence": 0.5,
                },
                model="test",
                provider="test",
            )

    class _StubGrounded:
        async def run(self, user_query):
            return GroundedPrecontext(
                summary="Grounded summary.",
                supporting_chunks=[GroundedChunk(uri="https://ai.google.dev/", title="docs", snippet="x")],
            )

    planner = PlannerAgent(search_client=_StubSearch(), llm_client=_StubLLM(), grounded_agent=_StubGrounded())
    output = asyncio.run(planner.plan("Find Gemini agent patterns"))

    assert output.grounded_precontext is not None
    assert output.grounded_precontext.summary == "Grounded summary."
    assert output.grounded_precontext.supporting_chunks[0].uri == "https://ai.google.dev/"
