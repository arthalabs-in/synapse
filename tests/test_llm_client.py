import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel

from backend.llm_client import (
    LLMClient,
    LLMConnectionError,
    LLMTimeoutError,
    LLMValidationError,
)


class AnswerSchema(BaseModel):
    answer: str
    confidence: float


def test_llm_client_reads_explicit_config():
    client = LLMClient(
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        model="qwen-test",
        timeout_seconds=12,
        transport=_transport_with_json({"answer": "ok", "confidence": 0.8}),
    )

    assert client.base_url == "http://localhost:8000/v1"
    assert client.api_key == "test-key"
    assert client.model == "qwen-test"
    assert client.timeout_seconds == 12


def test_chat_text_posts_openai_compatible_payload():
    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payloads.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        return _chat_response("plain text")

    client = LLMClient(
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        model="qwen-test",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.chat_text(
            [{"role": "user", "content": "hello"}],
            temperature=0.2,
            max_tokens=128,
        )
    )

    assert result == "plain text"
    assert seen_payloads[0]["model"] == "qwen-test"
    assert seen_payloads[0]["messages"][0]["content"] == "hello"
    assert seen_payloads[0]["temperature"] == 0.2
    assert seen_payloads[0]["max_tokens"] == 128


def test_chat_json_validates_schema_and_requests_json_output():
    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen_payloads.append(payload)
        return _chat_response('{"answer":"yes","confidence":0.9}')

    client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.chat_json(
            [{"role": "user", "content": "return json"}],
            AnswerSchema,
            temperature=0.3,
            max_tokens=256,
        )
    )

    assert result.answer == "yes"
    assert result.confidence == 0.9
    assert seen_payloads[0]["response_format"] == {"type": "json_object"}


def test_chat_json_extracts_json_from_markdown_fence():
    client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=_transport_with_content('```json\n{"answer":"yes","confidence":0.7}\n```'),
    )

    result = asyncio.run(
        client.chat_json(
            [{"role": "user", "content": "return json"}],
            AnswerSchema,
            temperature=0.3,
            max_tokens=256,
        )
    )

    assert result == AnswerSchema(answer="yes", confidence=0.7)


def test_chat_json_retries_once_with_stricter_settings_after_validation_failure():
    seen_payloads = []
    responses = iter(
        [
            _chat_response('{"answer":"missing confidence"}'),
            _chat_response('{"answer":"fixed","confidence":1.0}'),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payloads.append(json.loads(request.content))
        return next(responses)

    client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.chat_json(
            [{"role": "user", "content": "return json"}],
            AnswerSchema,
            temperature=0.8,
            max_tokens=256,
        )
    )

    assert result.answer == "fixed"
    assert len(seen_payloads) == 2
    assert seen_payloads[1]["temperature"] == 0
    assert "valid JSON" in seen_payloads[1]["messages"][-1]["content"]


def test_chat_json_raises_validation_error_after_retry_failure():
    client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=_transport_with_content('{"answer":"still invalid"}'),
    )

    with pytest.raises(LLMValidationError):
        asyncio.run(
            client.chat_json(
                [{"role": "user", "content": "return json"}],
                AnswerSchema,
                temperature=0.3,
                max_tokens=256,
            )
        )


def test_connection_and_timeout_errors_are_wrapped():
    def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cannot connect", request=request)

    def timeout_error(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("too slow", request=request)

    connect_client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=httpx.MockTransport(connect_error),
    )
    timeout_client = LLMClient(
        base_url="http://localhost:8000/v1",
        model="qwen-test",
        transport=httpx.MockTransport(timeout_error),
    )

    with pytest.raises(LLMConnectionError):
        asyncio.run(connect_client.chat_text([], temperature=0, max_tokens=10))

    with pytest.raises(LLMTimeoutError):
        asyncio.run(timeout_client.chat_text([], temperature=0, max_tokens=10))


def _transport_with_json(payload: dict) -> httpx.MockTransport:
    return _transport_with_content(json.dumps(payload))


def _transport_with_content(content: str) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: _chat_response(content))


def _chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
    )
