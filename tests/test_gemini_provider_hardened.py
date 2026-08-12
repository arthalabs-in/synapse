"""Phase 1.1 tests: Gemini reasoning telemetry, silent-truncation detection, thinking-budget payload, multimodal inline parts."""

import asyncio
import base64
import json

import httpx
import pytest

from backend.providers.llm.gemini import GeminiProvider
from backend.providers.llm.openai_compatible import EmptyVisibleContentError


def test_gemini_provider_raises_on_empty_visible_content_with_reasoning_tokens():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": []},
                        "finishReason": "MAX_TOKENS",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 50,
                    "candidatesTokenCount": 0,
                    "totalTokenCount": 2050,
                    "thoughtsTokenCount": 2000,
                },
            },
        )

    provider = GeminiProvider(
        api_key="secret",
        model="gemini-2.5-pro",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmptyVisibleContentError) as exc:
        asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}], max_tokens=2000))

    assert exc.value.reasoning_tokens == 2000
    call = provider.call_log[-1]
    assert call["finish_reason"] == "MAX_TOKENS"
    assert call["visible_chars"] == 0
    assert call["truncated_by_reasoning"] is True
    assert call["reasoning_tokens"] == 2000


def test_gemini_provider_records_finish_reason_and_visible_chars_on_success():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "hello world"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2, "totalTokenCount": 5, "thoughtsTokenCount": 1},
            },
        )

    provider = GeminiProvider(
        api_key="secret",
        model="gemini-2.5-pro",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}]))

    assert response.text == "hello world"
    call = provider.call_log[-1]
    assert call["finish_reason"] == "STOP"
    assert call["visible_chars"] == len("hello world")
    assert call["truncated_by_reasoning"] is False
    assert call["reasoning_tokens"] == 1
    assert response.usage.reasoning_tokens == 1


def test_gemini_provider_skips_thought_parts_in_visible_text():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "internal chain-of-thought", "thought": True},
                                {"text": "final answer"},
                            ]
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2, "thoughtsTokenCount": 5},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))

    response = asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}]))

    assert response.text == "final answer"


def test_gemini_thinking_budget_injected_only_when_env_set(monkeypatch):
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    # No env: thinkingConfig should be absent.
    monkeypatch.setattr("backend.providers.llm.gemini.config.GEMINI_THINKING_BUDGET", "")
    monkeypatch.setattr("backend.providers.llm.gemini.config.GEMINI_INCLUDE_THOUGHTS", False)
    provider_a = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))
    asyncio.run(provider_a.chat_text([{"role": "user", "content": "hi"}]))
    assert "thinkingConfig" not in seen["generationConfig"]

    # With env: thinkingBudget should appear and includeThoughts=True must propagate.
    seen.clear()
    monkeypatch.setattr("backend.providers.llm.gemini.config.GEMINI_THINKING_BUDGET", "1024")
    monkeypatch.setattr("backend.providers.llm.gemini.config.GEMINI_INCLUDE_THOUGHTS", True)
    provider_b = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))
    asyncio.run(provider_b.chat_text([{"role": "user", "content": "hi"}]))
    assert seen["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 1024, "includeThoughts": True}


def test_gemini_chat_multimodal_encodes_inline_bytes_as_base64():
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))

    payload_bytes = b"\x89PNGfake"
    asyncio.run(
        provider.chat_multimodal(
            [{"role": "user", "content": "describe this image"}],
            inline_parts=[{"mime_type": "image/png", "data": payload_bytes}],
        )
    )

    last_parts = seen["contents"][-1]["parts"]
    inline = [part for part in last_parts if "inlineData" in part]
    assert len(inline) == 1
    assert inline[0]["inlineData"]["mimeType"] == "image/png"
    assert inline[0]["inlineData"]["data"] == base64.b64encode(payload_bytes).decode("ascii")
    assert provider.call_log[-1]["inline_part_count"] == 1


def test_gemini_tools_field_propagates_when_provided():
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))

    asyncio.run(
        provider.chat_text(
            [{"role": "user", "content": "hi"}],
            tools=[{"googleSearch": {}}],
        )
    )

    assert seen["tools"] == [{"googleSearch": {}}]



def test_factory_uses_per_stage_model_envs(monkeypatch):
    """Phase 1.2: per-stage MODEL envs route to different providers.

    When ``EXTRACTION_MODEL`` or ``FACT_CHECKER_MODEL`` is set, the factory
    must return a Gemini provider bound to the stage-specific model while
    leaving unset stages on ``GEMINI_MODEL``.
    """
    from backend.providers.llm.factory import create_llm_provider

    monkeypatch.setattr("backend.providers.llm.factory.config.LLM_PROVIDER", "gemini")
    monkeypatch.setattr("backend.providers.llm.factory.config.GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setattr("backend.providers.llm.factory.config.SYNTHESIZER_PROVIDER", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.SYNTHESIZER_MODEL", "")

    # No per-stage overrides -> all stages share GEMINI_MODEL.
    monkeypatch.setattr("backend.providers.llm.factory.config.PLANNER_PROVIDER", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.PLANNER_MODEL", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.EXTRACTION_PROVIDER", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.EXTRACTION_MODEL", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.FACT_CHECKER_PROVIDER", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.FACT_CHECKER_MODEL", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.COVERAGE_AUDITOR_PROVIDER", "")
    monkeypatch.setattr("backend.providers.llm.factory.config.COVERAGE_AUDITOR_MODEL", "")

    assert create_llm_provider(stage="extraction").model == "gemini-2.5-pro"
    assert create_llm_provider(stage="fact_checker").model == "gemini-2.5-pro"

    # Set per-stage overrides and confirm each stage picks its own model.
    monkeypatch.setattr("backend.providers.llm.factory.config.EXTRACTION_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr("backend.providers.llm.factory.config.FACT_CHECKER_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr("backend.providers.llm.factory.config.PLANNER_MODEL", "gemini-2.5-pro")

    assert create_llm_provider(stage="extraction").model == "gemini-2.5-flash"
    assert create_llm_provider(stage="fact_checker").model == "gemini-2.5-flash"
    assert create_llm_provider(stage="planner").model == "gemini-2.5-pro"
    # Unset stage still uses the global default.
    assert create_llm_provider(stage="coverage_auditor").model == "gemini-2.5-pro"
