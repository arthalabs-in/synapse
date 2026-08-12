"""Phase 3.3: Gemini function-calling demo agent.

A small, optional side-panel (not part of the pipeline) that showcases
Gemini's native function-calling API. It exposes three tools backed by the
last pipeline run's fact ledger and (optionally) the existing search/fetch
providers. Single-turn loop: Gemini picks a tool, we execute, Gemini answers.

Gated by ``LIVE_TOOL_AGENT_ENABLED``. Tests stub the provider.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.providers.llm.gemini import GeminiProvider


FUNCTION_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "lookup_fact_ledger",
        "description": "Return verified / partial facts from the last pipeline run that match a keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Substring to match against fact claims."},
                "limit": {"type": "integer", "description": "Max number of facts to return (default 5)."},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "search_web",
        "description": "Run a web search via the project's configured search provider.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_source",
        "description": "Fetch readable text from a URL via the project's source fetcher.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


@dataclass
class LiveToolAgentAnswer:
    text: str
    citations: list[str]
    tool_calls: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "citations": self.citations, "tool_calls": self.tool_calls}


class LiveToolAgent:
    """Gemini function-calling demo agent backed by the last pipeline result."""

    def __init__(
        self,
        pipeline_result: dict[str, Any] | None = None,
        provider: GeminiProvider | None = None,
        search_provider: Any | None = None,
        source_fetcher: Any | None = None,
    ):
        self.pipeline_result = pipeline_result or {}
        self.provider = provider or GeminiProvider()
        self.search_provider = search_provider
        self.source_fetcher = source_fetcher
        self.tool_calls: list[dict[str, Any]] = []

    async def ask(self, question: str) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You can call three tools to answer the user: lookup_fact_ledger (preferred), "
                    "search_web, and fetch_source. Prefer the fact ledger first. Always cite URLs "
                    "when making factual claims. If no supporting evidence exists, say so plainly."
                ),
            },
            {"role": "user", "content": question},
        ]

        response = await self.provider.chat_text(
            messages,
            temperature=0,
            max_tokens=1500,
            tools=[{"functionDeclarations": FUNCTION_DECLARATIONS}],
        )

        function_call = _extract_function_call(response.raw_response or {})
        if not function_call:
            return LiveToolAgentAnswer(
                text=response.text.strip(),
                citations=_citations_from_text(response.text),
                tool_calls=[],
            ).to_dict()

        tool_name = function_call.get("name", "")
        tool_args = function_call.get("args") or {}
        tool_output = await self._dispatch_tool(tool_name, tool_args)
        self.tool_calls.append({"name": tool_name, "args": tool_args, "output": tool_output})

        messages.append({"role": "assistant", "content": json.dumps({"function_call": function_call})})
        messages.append({
            "role": "user",
            "content": (
                f"Function {tool_name} returned: {json.dumps(tool_output)[:6000]}.\n"
                "Compose a short answer with direct URL citations. Do not invent sources."
            ),
        })

        final = await self.provider.chat_text(messages, temperature=0, max_tokens=1500)
        return LiveToolAgentAnswer(
            text=final.text.strip(),
            citations=_citations_from_text(final.text) + _citations_from_tool_output(tool_output),
            tool_calls=list(self.tool_calls),
        ).to_dict()

    async def _dispatch_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "lookup_fact_ledger":
            return self._lookup_fact_ledger(args.get("keyword", ""), int(args.get("limit") or 5))
        if name == "search_web" and self.search_provider is not None:
            headers = await self.search_provider.search(args.get("query", ""), max_results=int(args.get("max_results") or 5))
            return {"results": [header.model_dump() if hasattr(header, "model_dump") else dict(header) for header in headers]}
        if name == "fetch_source" and self.source_fetcher is not None:
            # Not all fetchers support fetching a bare URL, so this demo is best-effort.
            try:
                fetched = await self.source_fetcher.fetch_many(
                    [{"result_id": "live_tool", "url": args.get("url", "")}]
                )
                return {"sources": [source.model_dump() if hasattr(source, "model_dump") else dict(source) for source in fetched]}
            except Exception as exc:
                return {"error": f"fetch failed: {exc}"}
        return {"error": f"tool '{name}' is unavailable in this environment"}

    def _lookup_fact_ledger(self, keyword: str, limit: int) -> dict[str, Any]:
        ledger = self.pipeline_result.get("fact_ledger") or {}
        facts = list(ledger.get("verified_facts") or []) + list(ledger.get("partial_facts") or [])
        keyword = (keyword or "").strip().lower()
        if keyword:
            facts = [fact for fact in facts if keyword in str(fact.get("claim", "")).lower()]
        return {"facts": facts[: max(1, limit)]}


def _extract_function_call(raw: dict[str, Any]) -> dict[str, Any] | None:
    candidates = raw.get("candidates") or []
    if not candidates:
        return None
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    for part in parts:
        if "functionCall" in part:
            return part["functionCall"]
    return None


def _citations_from_text(text: str) -> list[str]:
    import re

    return list({match for match in re.findall(r"https?://[^\s)]+", text or "")})


def _citations_from_tool_output(output: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for fact in output.get("facts", []) or []:
        urls.extend(fact.get("source_urls", []) or [])
    for source in output.get("sources", []) or []:
        url = source.get("url")
        if url:
            urls.append(url)
    for result in output.get("results", []) or []:
        url = result.get("url")
        if url:
            urls.append(url)
    # De-duplicate while preserving order.
    seen = set()
    deduped = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped
