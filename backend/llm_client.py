"""Legacy OpenAI-compatible client helpers.

New live pipeline code should use backend.providers.llm.factory. This module
remains for older tests and compatibility entrypoints.
"""

import asyncio
import json
from collections.abc import Sequence
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from config import config
from backend.providers.llm.gemini import GeminiProvider


class LLMConnectionError(RuntimeError):
    """Raised when the LLM server cannot be reached."""


class LLMTimeoutError(RuntimeError):
    """Raised when the LLM server does not respond before timeout."""


class LLMValidationError(RuntimeError):
    """Raised when JSON output cannot be parsed or validated."""


class LLMClient:
    """Async client for OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ):
        self.base_url = (base_url or config.OPENCODE_GO_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else config.OPENCODE_GO_API_KEY
        self.model = model or config.OPENCODE_GO_MODEL
        self.timeout_seconds = timeout_seconds or config.LLM_TIMEOUT_SECONDS
        self._transport = transport

    async def chat_text(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float,
        max_tokens: int,
        thinking_enabled: bool = False,
    ) -> str:
        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
        )
        data = await self._post_chat(payload)
        return self._extract_content(data)

    async def chat_json(
        self,
        messages: Sequence[dict[str, str]],
        schema: type[BaseModel],
        temperature: float,
        max_tokens: int,
        thinking_enabled: bool = False,
    ) -> BaseModel:
        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
            json_mode=True,
        )

        try:
            return await self._request_and_validate(payload, schema)
        except LLMValidationError as first_error:
            retry_payload = dict(payload)
            retry_payload["temperature"] = 0
            retry_payload["messages"] = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        "Return only valid JSON matching the requested schema. "
                        "Do not include markdown fences, commentary, or extra keys."
                    ),
                },
            ]
            try:
                return await self._request_and_validate(retry_payload, schema)
            except LLMValidationError as retry_error:
                raise LLMValidationError(str(retry_error)) from first_error

    async def _request_and_validate(self, payload: dict[str, Any], schema: type[BaseModel]) -> BaseModel:
        data = await self._post_chat(payload)
        content = self._extract_content(data)
        parsed = self._parse_json(content)
        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise LLMValidationError(f"LLM JSON failed schema validation: {exc}") from exc

    def _build_payload(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float,
        max_tokens: int,
        thinking_enabled: bool,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if thinking_enabled:
            payload["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
        return payload

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMConnectionError(f"LLM server returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMConnectionError("LLM request failed") from exc

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMValidationError("LLM response did not include message content") from exc

    def _parse_json(self, content: str) -> Any:
        text = content.strip()
        if text.startswith("```"):
            text = self._strip_markdown_fence(text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            extracted = self._extract_json_object(text)
            try:
                return json.loads(extracted)
            except json.JSONDecodeError as exc:
                raise LLMValidationError("LLM response was not valid JSON") from exc

    def _strip_markdown_fence(self, text: str) -> str:
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _extract_json_object(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMValidationError("LLM response did not contain a JSON object")
        return text[start : end + 1]


class VLLMClient(LLMClient):
    """Backward-compatible class name for older skeleton imports."""

    async def async_chat(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = config.TEMPERATURE,
        max_tokens: int = 2048,
    ) -> str:
        return await self.chat_text(messages, temperature, max_tokens)

    def chat(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = config.TEMPERATURE,
        max_tokens: int = 2048,
    ) -> str:
        return asyncio.run(self.async_chat(messages, temperature, max_tokens))

    def structured_chat(
        self,
        messages: Sequence[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        del response_format
        content = self.chat(messages, temperature, max_tokens)
        parsed = self._parse_json(content)
        if not isinstance(parsed, dict):
            raise LLMValidationError("LLM JSON response must be an object")
        return parsed


llm = GeminiProvider()
