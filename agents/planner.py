"""Planner agent for query interpretation and async research job design."""

import asyncio
import json
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict

from config import config
from backend.llm_client import llm
from backend.evidence_quality import build_evidence_criteria, infer_query_dimensions
from backend.models import GroundedPrecontext, PlannerOutput, SearchHeader
from backend.search_tools import SearchNoResultsError, search_client


class PlannerValidationError(RuntimeError):
    """Raised when planner output is unsafe or incomplete after retry."""


class LoosePlannerJSON(BaseModel):
    """Accept raw planner JSON so the agent can repair common LLM shape drift."""

    model_config = ConfigDict(extra="allow")


SYSTEM_PROMPT = """You are the Planner for SYNAPSE.

Search precontext has already been collected. Use it only to plan research.

Rules:
- Do not answer the user query.
- Do not invent citations.
- Every precontext claim must cite one provided source_id and source_url.
- Produce exactly 2 independent async ResearchJob objects.
- Each job must include objective, search_queries, must_answer, and source_priorities.
- Include evidence_criteria describing comparison_targets, decision_dimensions, preferred_source_types, avoid_source_patterns, source_fitness_terms, narrow_source_warnings, and coverage_requirements.
- Coverage requirements should make the answer auditable across the user's requested options and evaluation dimensions.
- Jobs must be detailed enough to execute independently.
- Search snippets are not evidence; use them only as planning context.
- Return JSON matching this exact shape:
{
  "original_query": "...",
  "query_type": "comparison|technical|general",
  "query_interpretation": "...",
  "precontext_claims": [{"claim": "...", "source_id": "result_id from precontext", "url": "url copied from precontext", "support_level": "weak"}],
  "evidence_criteria": {"comparison_targets": ["..."], "decision_dimensions": ["..."], "preferred_source_types": ["official", "paper"], "avoid_source_patterns": ["..."], "source_fitness_terms": ["..."], "narrow_source_warnings": ["..."], "coverage_requirements": [{"requirement_id": "req_01", "label": "...", "description": "...", "required_targets": ["..."], "required_dimensions": ["..."]}]},
  "research_jobs": [{"job_id": "job_a", "job_name": "...", "objective": "...", "search_queries": ["..."], "source_priorities": ["official", "paper"], "must_answer": ["..."]}],
  "coverage_checklist": ["..."],
  "planner_confidence": 0.0
}
"""


STRICT_RETRY_PROMPT = """FAILED VALIDATION.

Return corrected JSON only. Requirements:
- exactly 2 research_jobs
- at least 2 precontext_claims with URLs copied from provided precontext sources
- no invented citations or source ids
- every job has objective, search_queries, must_answer, and source_priorities
- include evidence_criteria with comparison targets, decision dimensions, and coverage requirements
- include coverage_checklist and planner_confidence
- do not answer the user's query
"""


class PlannerAgent:
    """Runs precontext search, then asks an LLM to plan two research jobs."""

    def __init__(self, search_client=search_client, llm_client=llm, grounded_agent: Any | None = None):
        self.search_client = search_client
        self.llm_client = llm_client
        # Phase 3.1: optional Gemini-native grounded precontext agent. Lazy-imported
        # in ``plan`` so the module is inert unless ``GEMINI_GROUNDING_ENABLED=true``.
        self._grounded_agent = grounded_agent
        self._grounded_precontext: GroundedPrecontext | None = None

    async def plan(self, user_query: str) -> PlannerOutput:
        precontext = await self._run_precontext_search(user_query)
        messages = self._build_messages(user_query, precontext)

        last_error = None
        allow_fallback = False
        for attempt in range(2):
            request_messages = messages if attempt == 0 else [*messages, {"role": "user", "content": STRICT_RETRY_PROMPT}]
            try:
                response = await self._chat_json_planner(
                    request_messages,
                    temperature=0.1 if attempt == 0 else 0,
                )
                if isinstance(response, PlannerOutput):
                    output = response
                else:
                    payload = response.parsed_json if hasattr(response, "parsed_json") else response.model_dump()
                    output = PlannerOutput.model_validate(self._coerce_payload(user_query, payload or {}, precontext))
                self._validate_output(output, precontext)
                if self._grounded_precontext is not None:
                    output.grounded_precontext = self._grounded_precontext
                output.evidence_criteria = build_evidence_criteria(user_query, output)
                return output
            except Exception as exc:
                last_error = exc
                if self._is_fallback_eligible_error(exc):
                    allow_fallback = True
                    break

        if allow_fallback:
            fallback = self._fallback_output(user_query, precontext)
            self._validate_output(fallback, precontext)
            if self._grounded_precontext is not None:
                fallback.grounded_precontext = self._grounded_precontext
            fallback.evidence_criteria = build_evidence_criteria(user_query, fallback)
            return fallback

        raise PlannerValidationError(f"Planner output failed validation: {last_error}") from last_error

    def _coerce_payload(self, user_query: str, payload: dict[str, Any], precontext: list[SearchHeader]) -> dict[str, Any]:
        fixed = dict(payload)
        fixed.setdefault("original_query", user_query)
        fixed.setdefault("query_type", "technical" if self._is_technical_query(user_query) else "general")
        fixed.setdefault("query_interpretation", fixed.get("interpretation") or f"Plan research for: {user_query}")
        fixed.setdefault("coverage_checklist", self._coverage_from_query(user_query))
        fixed.setdefault("planner_confidence", 0.5)
        fixed.setdefault("evidence_criteria", {})

        nested_claims = []
        jobs = fixed.get("research_jobs") or fixed.get("jobs") or []
        cleaned_jobs = []
        for index, job in enumerate(jobs[:2]):
            job = dict(job)
            nested_claims.extend(job.pop("precontext_claims", []) or [])
            cleaned_jobs.append(self._coerce_job(job, index, user_query))
        fixed["research_jobs"] = cleaned_jobs

        claims = fixed.get("precontext_claims") or nested_claims
        fixed["precontext_claims"] = self._coerce_claims(claims, precontext)
        provisional = PlannerOutput(
            original_query=user_query,
            query_type=fixed["query_type"],
            query_interpretation=fixed["query_interpretation"],
            precontext_claims=fixed["precontext_claims"],
            research_jobs=cleaned_jobs,
            coverage_checklist=fixed["coverage_checklist"],
            planner_confidence=float(fixed.get("planner_confidence", 0.5) or 0.5),
        )
        criteria = build_evidence_criteria(user_query, provisional)
        fixed["evidence_criteria"] = criteria.model_dump()
        fixed["research_jobs"] = [self._expand_job_queries(job, user_query, criteria) for job in fixed["research_jobs"]]
        return fixed

    def _expand_job_queries(self, job: dict[str, Any], user_query: str, criteria: Any) -> dict[str, Any]:
        queries = list(job.get("search_queries") or [])
        targets = list(criteria.comparison_targets or [])
        dimensions = list(criteria.decision_dimensions or [])
        for target in targets[:4]:
            queries.append(f"{target} {' '.join(dimensions[:3])} {self._domain_hint(user_query)}".strip())
        for dimension in dimensions[:5]:
            if targets:
                queries.append(f"{dimension} comparison {' vs '.join(targets[:3])} {self._domain_hint(user_query)}".strip())
        job["search_queries"] = _dedupe_text(queries)[:10]
        job["must_answer"] = _dedupe_text([*(job.get("must_answer") or []), *targets, *dimensions])[:16]
        return job

    def _domain_hint(self, user_query: str) -> str:
        query = user_query.lower()
        hints = []
        for marker in ["nonprofit", "grant", "policy brief", "small team", "citation", "privacy"]:
            if marker in query:
                hints.append(marker)
        return " ".join(hints[:4])

    async def _chat_json_planner(self, messages: list[dict[str, str]], *, temperature: float):
        try:
            return await self.llm_client.chat_json(
                messages,
                LoosePlannerJSON,
                temperature=temperature,
                max_tokens=64000,
                reasoning_effort="high",
            )
        except TypeError as exc:
            if "reasoning_effort" not in str(exc):
                raise
            return await self.llm_client.chat_json(
                messages,
                LoosePlannerJSON,
                temperature=temperature,
                max_tokens=64000,
            )

    def _coerce_job(self, job: dict[str, Any], index: int, user_query: str) -> dict[str, Any]:
        job_id = job.get("job_id") or ("job_a" if index == 0 else "job_b")
        return {
            "job_id": job_id,
            "job_name": job.get("job_name") or job.get("name") or f"{job_id} research",
            "objective": job.get("objective") or f"Research one independent angle of: {user_query}",
            "search_queries": list(job.get("search_queries") or job.get("queries") or [user_query]),
            "source_priorities": list(job.get("source_priorities") or ["official", "paper", "docs"]),
            "must_answer": list(job.get("must_answer") or self._coverage_from_query(user_query)),
            "avoid": list(job.get("avoid") or []),
            "evidence_requirements": job.get(
                "evidence_requirements",
                {"min_sources": 5, "require_quotes": True, "allow_snippet_only": False},
            ),
        }

    def _coerce_claims(self, claims: list[dict[str, Any]], precontext: list[SearchHeader]) -> list[dict[str, Any]]:
        by_url = {header.url: header for header in precontext}
        by_id = {header.result_id: header for header in precontext}
        fixed = []
        for claim in claims or []:
            claim = dict(claim)
            header = by_id.get(claim.get("source_id")) or by_url.get(claim.get("url") or claim.get("source_url"))
            if not header:
                continue
            fixed.append(
                {
                    "claim": claim.get("claim") or header.snippet or header.title,
                    "source_id": header.result_id,
                    "url": header.url,
                    "support_level": claim.get("support_level", "weak"),
                }
            )
        for header in precontext:
            if len(fixed) >= 2:
                break
            if any(item["source_id"] == header.result_id for item in fixed):
                continue
            fixed.append(
                {
                    "claim": header.snippet or header.title,
                    "source_id": header.result_id,
                    "url": header.url,
                    "support_level": "weak",
                }
            )
        return fixed[:5]

    def _coverage_from_query(self, user_query: str) -> list[str]:
        query = user_query.lower()
        checklist = []
        for candidate in [
            "reliability",
            "citation quality",
            "cost",
            "implementation",
            "usability",
            "privacy",
            "maintainability",
            "memory",
            "throughput",
            "software",
            "deployment",
            "power",
            "availability",
        ]:
            if candidate in query:
                checklist.append(candidate)
        for dimension in infer_query_dimensions(user_query):
            if dimension not in checklist:
                checklist.append(dimension)
        return checklist or ["source support", "tradeoffs", "limitations"]

    def _fallback_output(self, user_query: str, precontext: list[SearchHeader]) -> PlannerOutput:
        """Build a deterministic, citation-safe plan from real precontext when LLM planning fails."""
        coverage = self._coverage_from_query(user_query)
        claims = self._coerce_claims([], precontext)
        return PlannerOutput(
            original_query=user_query,
            query_type="technical" if self._is_technical_query(user_query) else "general",
            query_interpretation=f"Research source-grounded options, tradeoffs, and limitations for: {user_query}",
            precontext_claims=claims,
            planning_risks=["LLM planner failed, timed out, or was rate limited; deterministic fallback plan used."],
            research_jobs=[
                {
                    "job_id": "job_a",
                    "job_name": "Official and primary-source evidence",
                    "objective": f"Find quote-grounded official, primary, or directly relevant source evidence for {user_query}.",
                    "search_queries": [
                        user_query,
                        f"{user_query} official documentation",
                        f"{user_query} requirements criteria",
                    ],
                    "source_priorities": ["official", "docs", "primary", "paper"],
                    "must_answer": coverage + ["requirements", "constraints", "source support"],
                    "evidence_requirements": {"min_sources": 3, "require_quotes": True, "allow_snippet_only": False, "max_results_per_query": 5},
                },
                {
                    "job_id": "job_b",
                    "job_name": "Implementation and tradeoff evidence",
                    "objective": f"Find quote-grounded implementation, feasibility, differentiation, and tradeoff evidence for {user_query}.",
                    "search_queries": [
                        f"{user_query} implementation examples",
                        f"{user_query} agent workflow architecture",
                        f"{user_query} risks limitations evaluation",
                    ],
                    "source_priorities": ["official", "docs", "paper", "case study"],
                    "must_answer": coverage + ["implementation", "differentiation", "risks"],
                    "evidence_requirements": {"min_sources": 3, "require_quotes": True, "allow_snippet_only": False, "max_results_per_query": 5},
                },
            ],
            coverage_checklist=coverage,
            evidence_criteria=build_evidence_criteria(
                user_query,
                PlannerOutput(
                    original_query=user_query,
                    query_interpretation=f"Research source-grounded options, tradeoffs, and limitations for: {user_query}",
                    precontext_claims=claims,
                    research_jobs=[],
                    coverage_checklist=coverage,
                ),
            ),
            planner_confidence=0.45,
        )

    def _is_fallback_eligible_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        transient_markers = {
            "timeout",
            "connection",
            "connect",
            "429",
            "too many requests",
            "rate limit",
            "temporarily unavailable",
            "server error",
            "http 5",
            "empty visible content",
            "finish_reason=length",
            "truncated_by_reasoning",
            "jsondecodeerror",
            "expecting ',' delimiter",
        }
        return isinstance(exc, TimeoutError) or any(marker in message for marker in transient_markers)

    async def _run_precontext_search(self, user_query: str) -> list[SearchHeader]:
        web_queries = self._precontext_web_queries(user_query)
        headers: list[SearchHeader] = []

        web_tasks = [self._safe_precontext_search(query, max_results=3, arxiv=False) for query in web_queries]

        # Phase 3.1: kick off Gemini Search grounding in parallel when enabled.
        grounded_task = self._safe_grounded_precontext(user_query) if config.GEMINI_GROUNDING_ENABLED else None

        web_batches = await asyncio.gather(*web_tasks)
        for batch in web_batches:
            headers.extend(batch)

        if self._is_technical_query(user_query):
            arxiv_tasks = [self._safe_precontext_search(query, max_results=2, arxiv=True) for query in self._precontext_arxiv_queries(user_query)]
            for batch in await asyncio.gather(*arxiv_tasks):
                headers.extend(batch)

        if grounded_task is not None:
            self._grounded_precontext = await grounded_task

        return self._dedupe_precontext(headers)[:10]

    async def _safe_grounded_precontext(self, user_query: str) -> GroundedPrecontext | None:
        try:
            if self._grounded_agent is None:
                from agents.grounded_precontext import GroundedPrecontextAgent

                self._grounded_agent = GroundedPrecontextAgent()
            return await self._grounded_agent.run(user_query)
        except Exception:
            return None

    async def _safe_precontext_search(self, query: str, max_results: int, arxiv: bool) -> list[SearchHeader]:
        try:
            if arxiv:
                if hasattr(self.search_client, "search_arxiv"):
                    return await self.search_client.search_arxiv(query, max_results=max_results)
                return [h for h in await self.search_client.search(query, max_results=max_results) if h.provider == "arxiv"]
            if hasattr(self.search_client, "search_web"):
                return await self.search_client.search_web(query, max_results=max_results)
            return [h for h in await self.search_client.search(query, max_results=max_results) if h.provider != "arxiv"]
        except SearchNoResultsError:
            return []

    def _precontext_web_queries(self, user_query: str) -> list[str]:
        return [
            user_query,
            f"{user_query} official documentation",
            f"{user_query} recent analysis",
        ]

    def _precontext_arxiv_queries(self, user_query: str) -> list[str]:
        return [user_query]

    def _is_technical_query(self, user_query: str) -> bool:
        technical_terms = {
            "ai",
            "algorithm",
            "architecture",
            "benchmark",
            "biology",
            "compute",
            "gpu",
            "inference",
            "llm",
            "model",
            "paper",
            "physics",
            "research",
            "scientific",
            "transformer",
        }
        query = user_query.lower()
        return any(term in query for term in technical_terms)

    def _build_messages(self, user_query: str, precontext: list[SearchHeader]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User query:\n{user_query}\n\n"
                    "Precontext SearchHeader objects:\n"
                    f"{json.dumps([header.model_dump() for header in precontext], indent=2)}\n\n"
                    "Create PlannerOutput JSON."
                ),
            },
        ]

    def _validate_output(self, output: PlannerOutput, precontext: list[SearchHeader]) -> None:
        source_urls_by_id = {header.result_id: header.url for header in precontext}
        source_urls = set(source_urls_by_id.values())

        cited_claims = [claim for claim in output.precontext_claims if claim.url]
        if len(cited_claims) < 2:
            raise PlannerValidationError("at least 2 precontext claims must include URLs")

        for claim in cited_claims:
            if claim.source_id not in source_urls_by_id:
                raise PlannerValidationError(f"precontext claim cites unknown source_id: {claim.source_id}")
            if claim.url not in source_urls:
                raise PlannerValidationError(f"precontext claim cites unknown URL: {claim.url}")
            if source_urls_by_id[claim.source_id] != claim.url:
                raise PlannerValidationError(f"precontext source_id/url mismatch: {claim.source_id}")

        if len(output.research_jobs) != 2:
            raise PlannerValidationError("planner must create exactly 2 research jobs")

        for job in output.research_jobs:
            missing = []
            if not job.objective:
                missing.append("objective")
            if not job.search_queries:
                missing.append("search_queries")
            if not job.must_answer:
                missing.append("must_answer")
            if not job.source_priorities:
                missing.append("source_priorities")
            if missing:
                raise PlannerValidationError(f"research job {job.job_id} missing: {', '.join(missing)}")

    def _dedupe_precontext(self, headers: Iterable[SearchHeader]) -> list[SearchHeader]:
        seen = set()
        deduped = []
        for header in headers:
            if header.url in seen:
                continue
            seen.add(header.url)
            deduped.append(header)
        return deduped


async def async_plan(user_query: str) -> PlannerOutput:
    """Async compatibility entrypoint."""
    return await PlannerAgent().plan(user_query)


def plan(user_query: str) -> PlannerOutput:
    """Synchronous compatibility entrypoint for the current skeleton."""
    return asyncio.run(async_plan(user_query))


def _dedupe_text(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        text = " ".join(str(value).split())
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out
