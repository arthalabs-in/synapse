"""Generic OpenAI-compatible /chat/completions provider."""

import json
import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from config import config
from backend.models import LLMResponse, LLMUsage


class EmptyVisibleContentError(RuntimeError):
    """Raised when a provider spent tokens but returned no visible assistant text."""

    def __init__(
        self,
        *,
        finish_reason: str | None,
        reasoning_tokens: int | None,
        completion_tokens: int | None,
        max_tokens: int,
    ):
        self.finish_reason = finish_reason
        self.reasoning_tokens = reasoning_tokens
        self.completion_tokens = completion_tokens
        self.max_tokens = max_tokens
        super().__init__(
            "LLM returned empty visible content "
            f"(finish_reason={finish_reason}, reasoning_tokens={reasoning_tokens}, "
            f"completion_tokens={completion_tokens}, max_tokens={max_tokens})"
        )


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        provider: str = "openai_compatible",
        auth_header: str = "Authorization",
        auth_scheme: str = "Bearer",
        timeout_seconds: float = 60,
        response_format_json: bool = True,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
        max_concurrent_calls: int | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.provider = provider
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.timeout_seconds = timeout_seconds
        self.response_format_json = response_format_json
        self.transport = transport
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.call_log: list[dict[str, Any]] = []
        self._call_counter = 0
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_calls or config.LLM_MAX_CONCURRENT_CALLS))

    async def chat_text(self, messages: list[dict], temperature: float = 0.2, max_tokens: int = 1000, **kwargs) -> LLMResponse:
        return await self._chat(messages, temperature, max_tokens, schema=None, json_mode=False, **kwargs)

    async def chat_json(self, messages: list[dict], schema: type[BaseModel], temperature: float = 0.2, max_tokens: int = 1000, **kwargs) -> LLMResponse:
        try:
            return await self._chat(messages, temperature, max_tokens, schema=schema, json_mode=True, **kwargs)
        except (json.JSONDecodeError, ValueError):
            strict = [
                *messages,
                {"role": "user", "content": "Return only valid JSON matching the requested schema. No markdown."},
            ]
            return await self._chat(strict, 0, max_tokens, schema=schema, json_mode=True, **kwargs)

    async def _chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        schema: type[BaseModel] | None,
        json_mode: bool,
        **kwargs,
    ) -> LLMResponse:
        self._call_counter += 1
        call_index = self._call_counter
        schema_name = schema.__name__ if schema else None
        skills = [str(skill).strip() for skill in (kwargs.get("skills") or []) if str(skill).strip()]
        messages = _messages_with_skills(messages, skills)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if kwargs.get("reasoning_effort"):
            payload["reasoning_effort"] = kwargs["reasoning_effort"]
        if kwargs.get("reasoning"):
            payload["reasoning"] = kwargs["reasoning"]
        if json_mode and self.response_format_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {}
        if self.api_key:
            headers[self.auth_header] = f"{self.auth_scheme} {self.api_key}".strip()
        start = perf_counter()
        wall_start = datetime.now(timezone.utc)
        log_entry: dict[str, Any] = {
            "call_index": call_index,
            "provider": self.provider,
            "model": self.model,
            "schema": schema_name,
            "json_mode": json_mode,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "message_count": len(messages),
            "skill_count": len(skills),
            "wall_start": wall_start.isoformat(),
        }
        try:
            async def send_request():
                async with self._semaphore:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                        response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                        log_entry["http_status"] = response.status_code
                        response.raise_for_status()
                        return response.json()

            raw = await asyncio.wait_for(send_request(), timeout=config.LLM_STAGE_TIMEOUT_SECONDS)
            latency = round((perf_counter() - start) * 1000, 2)
            choice = (raw.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            finish_reason = choice.get("finish_reason")
            usage = _usage(raw.get("usage") or {})
            text = _extract_message_content(message)
            visible_chars = len(text.strip())
            truncated_by_reasoning = bool(
                usage
                and visible_chars == 0
                and (
                    finish_reason == "length"
                    or (usage.completion_tokens or 0) >= max_tokens
                    or (usage.reasoning_tokens or 0) > 0
                )
            )
            if usage:
                self._add_usage(usage)
            log_entry.update(
                {
                    "latency_ms": latency,
                    "wall_end": datetime.now(timezone.utc).isoformat(),
                    "finish_reason": finish_reason,
                    "reasoning_tokens": usage.reasoning_tokens if usage else None,
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None,
                    "response_chars": len(text),
                    "visible_chars": visible_chars,
                    "reasoning_content_chars": len(str(message.get("reasoning_content") or "")),
                    "truncated_by_reasoning": truncated_by_reasoning,
                }
            )
            if visible_chars == 0 and usage and (usage.total_tokens or usage.completion_tokens):
                raise EmptyVisibleContentError(
                    finish_reason=finish_reason,
                    reasoning_tokens=usage.reasoning_tokens,
                    completion_tokens=usage.completion_tokens,
                    max_tokens=max_tokens,
                )
            parsed = _parse_json(text) if schema else None
            if schema:
                try:
                    schema.model_validate(parsed)
                except ValidationError as exc:
                    raise ValueError(f"LLM JSON failed schema validation: {exc}") from exc
            log_entry.update(
                {
                    "ok": True,
                }
            )
            return LLMResponse(
                text=text,
                parsed_json=parsed,
                model=self.model,
                provider=self.provider,
                usage=usage,
                latency_ms=latency,
                raw_response=raw,
            )
        except Exception as exc:
            log_entry.update(
                {
                    "ok": False,
                    "latency_ms": round((perf_counter() - start) * 1000, 2),
                    "wall_end": datetime.now(timezone.utc).isoformat(),
                    "error_type": exc.__class__.__name__,
                    "error": str(exc)[:500],
                }
            )
            raise
        finally:
            self.call_log.append(log_entry)

    def _add_usage(self, usage: LLMUsage) -> None:
        self.token_usage["prompt_tokens"] += usage.prompt_tokens or 0
        self.token_usage["completion_tokens"] += usage.completion_tokens or 0
        self.token_usage["total_tokens"] += usage.total_tokens or 0


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(cleaned[start : end + 1])


def _extract_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, dict):
                texts.append(str(part.get("text") or ""))
        return "".join(texts)
    return str(content)


def _messages_with_skills(messages: list[dict], skills: list[str]) -> list[dict]:
    if not skills:
        return messages
    skill_text = "\n\n".join(f"<skill>\n{skill}\n</skill>" for skill in skills)
    skill_message = {
        "role": "system",
        "content": "Use the following skill guidance for this call:\n\n" + skill_text,
    }
    return [skill_message, *messages]


def _usage(raw: dict[str, Any]) -> LLMUsage | None:
    if not raw:
        return None
    completion_details = raw.get("completion_tokens_details") or {}
    return LLMUsage(
        prompt_tokens=raw.get("prompt_tokens"),
        completion_tokens=raw.get("completion_tokens"),
        total_tokens=raw.get("total_tokens"),
        reasoning_tokens=completion_details.get("reasoning_tokens"),
        raw=raw,
    )
