"""Phase 3.3 tests: Gemini function-calling demo agent."""

import asyncio
import json

import httpx

from agents.live_tool_agent import LiveToolAgent
from backend.providers.llm.gemini import GeminiProvider


def _transport_with_function_call_flow():
    call_count = {"count": 0}

    async def handler(request):
        call_count["count"] += 1
        body = json.loads(request.read().decode())
        # First Gemini call: the model should receive the tool declarations.
        if call_count["count"] == 1:
            assert "tools" in body
            assert body["tools"][0]["functionDeclarations"][0]["name"] == "lookup_fact_ledger"
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "lookup_fact_ledger",
                                            "args": {"keyword": "mi300", "limit": 3},
                                        }
                                    }
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
                },
            )
        # Second call: model should see the tool output and answer with citations.
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "MI300X ships with 192GB of HBM3 memory "
                                        "(https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html)."
                                    )
                                }
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
            },
        )

    return httpx.MockTransport(handler)


def test_live_tool_agent_dispatches_lookup_fact_ledger_and_cites_urls():
    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=_transport_with_function_call_flow())
    pipeline_result = {
        "fact_ledger": {
            "verified_facts": [
                {
                    "fact_id": "fact_001",
                    "claim": "MI300X has 192GB HBM3 memory.",
                    "source_urls": ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"],
                }
            ],
            "partial_facts": [],
        }
    }

    agent = LiveToolAgent(pipeline_result=pipeline_result, provider=provider)
    answer = asyncio.run(agent.ask("How much memory does MI300X have?"))

    assert "MI300X" in answer["text"]
    # Citation URL should appear in the citations list.
    assert any(url.endswith("mi300x.html") for url in answer["citations"])
    # Exactly one tool call was executed.
    assert len(answer["tool_calls"]) == 1
    assert answer["tool_calls"][0]["name"] == "lookup_fact_ledger"
    assert answer["tool_calls"][0]["args"] == {"keyword": "mi300", "limit": 3}


def test_live_tool_agent_handles_no_function_call_as_direct_text():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "No tool needed: the answer is 42."}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))
    agent = LiveToolAgent(pipeline_result={}, provider=provider)

    answer = asyncio.run(agent.ask("Trivial question"))

    assert answer["text"] == "No tool needed: the answer is 42."
    assert answer["tool_calls"] == []
