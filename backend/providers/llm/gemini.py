"""Gemini API provider for SYNAPSE live research."""

import asyncio
import base64
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from config import config
from backend.models import LLMResponse, LLMUsage
from backend.providers.llm.openai_compatible import EmptyVisibleContentError, _parse_json


class GeminiProvider:
    provider = "gemini"

    def __init__(
        self,
        api_key: str = config.GEMINI_API_KEY,
        model: str = config.GEMINI_MODEL,
        base_url: str = config.GEMINI_BASE_URL,
        timeout_seconds: float = config.LLM_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
        max_concurrent_calls: int | None = None,
    ):
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.call_log: list[dict[str, Any]] = []
        self._call_counter = 0
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_calls or config.LLM_MAX_CONCURRENT_CALLS))

    async def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        return await self._chat(messages, temperature, max_tokens, schema=None, json_mode=False, **kwargs)

    async def chat_json(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        try:
            return await self._chat(messages, temperature, max_tokens, schema=schema, json_mode=True, **kwargs)
        except (json.JSONDecodeError, ValueError):
            strict = [
                *messages,
                {"role": "user", "content": "Return only valid JSON matching the requested schema. No markdown."},
            ]
            return await self._chat(strict, 0, max_tokens, schema=schema, json_mode=True, **kwargs)

    async def chat_multimodal(
        self,
        messages: list[dict],
        inline_parts: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Phase 3.2: multimodal generateContent call.

        ``inline_parts`` is a list of ``{"mime_type": str, "data": bytes | str}``
        entries. Bytes are base64-encoded automatically.
        """
        return await self._chat(
            messages,
            temperature,
            max_tokens,
            schema=None,
            json_mode=False,
            inline_parts=inline_parts,
            **kwargs,
        )

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
        inline_parts = kwargs.get("inline_parts") or []
        extra_tools = kwargs.get("tools") or []
        payload = _build_payload(
            messages,
            temperature,
            max_tokens,
            json_mode,
            skills=skills,
            inline_parts=inline_parts,
            extra_tools=extra_tools,
        )
        headers = {"x-goog-api-key": self.api_key} if self.api_key else {}
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
            "inline_part_count": len(inline_parts),
            "wall_start": wall_start.isoformat(),
        }
        try:
            async def send_request() -> dict[str, Any]:
                async with self._semaphore:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                        response = await client.post(
                            f"{self.base_url}/models/{self.model}:generateContent",
                            json=payload,
                            headers=headers,
                        )
                        log_entry["http_status"] = response.status_code
                        response.raise_for_status()
                        return response.json()

            raw = await asyncio.wait_for(send_request(), timeout=config.LLM_STAGE_TIMEOUT_SECONDS)
            latency = round((perf_counter() - start) * 1000, 2)
            text, finish_reason, grounding_metadata = _extract_text(raw, allow_empty=True)
            visible_chars = len(text.strip())
            has_function_call = _has_function_call(raw)
            usage = _usage(raw.get("usageMetadata") or {})
            truncated_by_reasoning = bool(
                usage
                and visible_chars == 0
                and not has_function_call
                and (
                    finish_reason == "MAX_TOKENS"
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
                    "truncated_by_reasoning": truncated_by_reasoning,
                    "grounded": bool(grounding_metadata),
                    "function_call": has_function_call,
                }
            )
            if (
                visible_chars == 0
                and not has_function_call
                and usage
                and (usage.total_tokens or usage.completion_tokens)
            ):
                raise EmptyVisibleContentError(
                    finish_reason=finish_reason,
                    reasoning_tokens=usage.reasoning_tokens,
                    completion_tokens=usage.completion_tokens,
                    max_tokens=max_tokens,
                )
            if not text and not has_function_call:
                raise ValueError("Gemini response did not include text parts")
            parsed = _parse_json(text) if schema else None
            if schema:
                try:
                    schema.model_validate(parsed)
                except ValidationError as exc:
                    raise ValueError(f"Gemini JSON failed schema validation: {exc}") from exc
            log_entry["ok"] = True
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


def _build_payload(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    skills: list[str] | None = None,
    inline_parts: list[dict[str, Any]] | None = None,
    extra_tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    system_text: list[str] = []
    for skill in skills or []:
        system_text.append(f"Use the following skill guidance for this call:\n\n<skill>\n{skill}\n</skill>")
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        text = str(message.get("content", ""))
        if role == "system":
            system_text.append(text)
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )

    if inline_parts:
        if not contents:
            contents.append({"role": "user", "parts": []})
        last_parts = contents[-1]["parts"]
        for part in inline_parts:
            data = part.get("data")
            if isinstance(data, (bytes, bytearray)):
                encoded = base64.b64encode(bytes(data)).decode("ascii")
            else:
                encoded = str(data or "")
            last_parts.append(
                {
                    "inlineData": {
                        "mimeType": part.get("mime_type") or part.get("mimeType") or "application/octet-stream",
                        "data": encoded,
                    }
                }
            )

    payload: dict[str, Any] = {
        "contents": contents or [{"role": "user", "parts": [{"text": ""}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    # Phase 1.1: optional thinking-budget injection. Empty env preserves prior behavior.
    raw_budget = (config.GEMINI_THINKING_BUDGET or "").strip()
    if raw_budget != "":
        try:
            budget = int(raw_budget)
            thinking_cfg: dict[str, Any] = {"thinkingBudget": budget}
            if config.GEMINI_INCLUDE_THOUGHTS:
                thinking_cfg["includeThoughts"] = True
            payload["generationConfig"]["thinkingConfig"] = thinking_cfg
        except ValueError:
            # Silently skip a malformed budget; keep the call unchanged.
            pass

    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_text)}]}

    if extra_tools:
        payload["tools"] = list(extra_tools)

    return payload


def _extract_text(raw: dict[str, Any], *, allow_empty: bool = False) -> tuple[str, str | None, dict[str, Any] | None]:
    candidates = raw.get("candidates") or []
    if not candidates:
        if allow_empty:
            return "", None, None
        raise ValueError("Gemini response did not include candidates")
    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    parts = ((candidate.get("content") or {}).get("parts") or [])
    texts: list[str] = []
    for part in parts:
        text = part.get("text")
        if text:
            # Skip "thought" parts so reasoning tokens never leak into visible text.
            if part.get("thought"):
                continue
            texts.append(str(text))
    if not texts and not allow_empty:
        raise ValueError("Gemini response did not include text parts")
    grounding = candidate.get("groundingMetadata")
    return "".join(texts), finish_reason, grounding


def _usage(raw: dict[str, Any]) -> LLMUsage | None:
    if not raw:
        return None
    # Gemini exposes ``thoughtsTokenCount`` alongside candidates/prompt counts.
    thoughts = raw.get("thoughtsTokenCount")
    return LLMUsage(
        prompt_tokens=raw.get("promptTokenCount"),
        completion_tokens=raw.get("candidatesTokenCount"),
        total_tokens=raw.get("totalTokenCount"),
        reasoning_tokens=thoughts,
        raw=raw,
    )


def _has_function_call(raw: dict[str, Any]) -> bool:
    candidates = raw.get("candidates") or []
    if not candidates:
        return False
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    return any("functionCall" in part for part in parts)
