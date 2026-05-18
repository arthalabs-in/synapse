"""Async orchestration for the SYNAPSE research pipeline."""

import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from config import config
from agents.evidence_extractor import EvidenceExtractorAgent
from agents.fact_checker import FactCheckerAgent
from agents.gap_detector import CoverageAuditorAgent
from agents.planner import PlannerAgent
from agents.searcher import SearcherAgent
from agents.synthesizer import SynthesisDegradedError, SynthesizerAgent
from backend.evidence_quality import build_coverage_matrix, build_evidence_criteria
from backend.models import (
    CoveragePatch,
    EvidenceItem,
    FactLedger,
    JobEvidenceOutput,
    JobSearchOutput,
    PipelineResult,
    PlannerOutput,
    ResearchJob,
    ResearchReport,
    SearchHeader,
)
from backend.patch_applicator import apply_patch
from backend.patch_applicator import PatchApplicationError
from backend.reranker import rank_fetched_sources, rank_search_headers
from backend.providers.browser.camofox_client import CamofoxClient
from backend.providers.browser.html_fetcher import HtmlFetcher
from backend.providers.llm.factory import create_llm_provider
from backend.providers.search.arxiv_provider import ArxivProvider
from backend.providers.search.composite_search import CompositeSearchProvider
from backend.providers.search.duckduckgo_provider import DuckDuckGoProvider
from backend.providers.sources.fetcher import SourceFetcher


class SynapseResearchEngine:
    """Coordinates planner, research jobs, fact checking, synthesis, and patching."""

    def __init__(
        self,
        planner_agent: Any | None = None,
        searcher_agent: Any | None = None,
        evidence_extractor_agent: Any | None = None,
        fact_checker_agent: Any | None = None,
        synthesizer_agent: Any | None = None,
        coverage_auditor_agent: Any | None = None,
        patch_applicator: Callable[[ResearchReport, CoveragePatch, FactLedger], Any] = apply_patch,
        search_provider: Any | None = None,
        source_fetcher: SourceFetcher | None = None,
        llm_provider: Any | None = None,
        demo_mode: bool | None = None,
        golden_result_path: str | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.llm_provider = llm_provider or self._safe_llm_provider()
        self.synthesizer_llm_provider = self._synthesizer_provider(llm_provider)
        # Phase 1.2: per-stage providers. Each reuses self.llm_provider unless the
        # matching env override is set (PLANNER_MODEL, EXTRACTION_MODEL, etc.).
        self.planner_llm_provider = self._stage_provider("planner", llm_provider)
        self.extraction_llm_provider = self._stage_provider("extraction", llm_provider)
        self.fact_checker_llm_provider = self._stage_provider("fact_checker", llm_provider)
        self.coverage_auditor_llm_provider = self._stage_provider("coverage_auditor", llm_provider)
        self.search_provider = search_provider or CompositeSearchProvider([DuckDuckGoProvider(), ArxivProvider()])
        self.source_fetcher = source_fetcher or SourceFetcher(HtmlFetcher(), CamofoxClient())
        self.planner_agent = planner_agent or PlannerAgent(search_client=self.search_provider, llm_client=self.planner_llm_provider)
        self.searcher_agent = searcher_agent or SearcherAgent(search_client=self.search_provider)
        self.evidence_extractor_agent = evidence_extractor_agent or EvidenceExtractorAgent(llm_provider=self.extraction_llm_provider)
        self.fact_checker_agent = fact_checker_agent or FactCheckerAgent(llm_provider=self.fact_checker_llm_provider)
        self.synthesizer_agent = synthesizer_agent or SynthesizerAgent(llm_provider=self.synthesizer_llm_provider)
        self.coverage_auditor_agent = coverage_auditor_agent or CoverageAuditorAgent(llm_provider=self.coverage_auditor_llm_provider)
        self.patch_applicator = patch_applicator
        self.demo_mode = config.DEMO_MODE if demo_mode is None else demo_mode
        self.golden_result_path = golden_result_path or config.GOLDEN_RESULT_PATH
        self.profile_events: list[dict[str, Any]] = []
        self.progress_callback = progress_callback

    async def run(
        self,
        research_question: str,
        uploads: list[dict[str, Any]] | None = None,
    ) -> PipelineResult:
        """Run the full pipeline and return a typed PipelineResult.

        ``uploads`` is additive (Phase 3.2). When ``MULTIMODAL_ENABLED=true`` and
        uploads are supplied, a multimodal ingestor runs first and contributes
        additional quote-anchored evidence before the usual search fan-out.
        """
        if self.demo_mode:
            return self._load_golden_result()

        timings: dict[str, float] = {}
        errors: list[dict[str, Any]] = []
        self._fetched_sources: list[Any] = []
        self.profile_events = []
        self.current_stage = "starting"
        total_start = perf_counter()

        # Phase 3.2: multimodal pre-stage (inert unless flag is on and files are staged).
        uploads = uploads or []
        multimodal_evidence: list[EvidenceItem] = []
        upload_metadata: list[dict[str, Any]] = []
        if uploads and config.MULTIMODAL_ENABLED:
            try:
                from agents.multimodal_ingestor import MultimodalIngestorAgent

                ingestor = MultimodalIngestorAgent(llm_provider=self.llm_provider)
                multimodal_result = await self._timed(
                    "multimodal_ingestor",
                    timings,
                    ingestor.ingest(research_question, uploads),
                )
                multimodal_evidence = multimodal_result.evidence_items
                upload_metadata = multimodal_result.upload_metadata
            except Exception as exc:
                errors.append({"stage": "multimodal_ingestor", "error": str(exc)[:400]})

        self.current_stage = "planner"
        planner_output = await self._timed("planner", timings, self.planner_agent.plan(research_question))
        planner_output.evidence_criteria = build_evidence_criteria(research_question, planner_output)
        self._validate_planner_jobs(planner_output)

        self.current_stage = "research_jobs"
        job_results, job_errors = await self._timed(
            "research_jobs",
            timings,
            self._run_research_jobs(research_question, planner_output.research_jobs[:2]),
        )
        errors.extend(job_errors)
        degraded = bool(job_errors)

        search_headers = [header for search_out, _ in job_results for header in search_out.search_headers]
        evidence_items = [item for _, evidence_out in job_results for item in evidence_out.evidence_items]
        # Phase 3.2: merge user-upload evidence into the ledger input.
        if multimodal_evidence:
            evidence_items = list(multimodal_evidence) + evidence_items
        fetched_sources = list(getattr(self, "_fetched_sources", []))
        job_summaries = [self._job_summary(search_out, evidence_out) for search_out, evidence_out in job_results]

        self.current_stage = "fact_checker"
        fact_ledger = await self._timed(
            "fact_checker",
            timings,
            self.fact_checker_agent.check(
                original_query=research_question,
                planner_output=planner_output,
                research_job_outputs=job_results,
                search_headers=search_headers,
                evidence_items=evidence_items,
            ),
        )
        coverage_matrix = build_coverage_matrix(planner_output, evidence_items, fact_ledger)

        self.current_stage = "synthesizer"
        try:
            report_v1 = await self._timed(
                "synthesizer",
                timings,
                self._synthesize_report(
                    self.synthesizer_agent,
                    original_query=research_question,
                    planner_output=planner_output,
                    job_summaries=job_summaries,
                    fact_ledger=fact_ledger,
                    coverage_matrix=coverage_matrix,
                ),
            )
        except SynthesisDegradedError as exc:
            errors.append({"stage": "synthesizer", "error": str(exc), "degraded_mode": "synthesis_empty_visible_content"})
            degraded = True
            fallback_synthesizer = SynthesizerAgent()
            report_v1 = await self._timed(
                "synthesizer_fallback",
                timings,
                self._synthesize_report(
                    fallback_synthesizer,
                    original_query=research_question,
                    planner_output=planner_output,
                    job_summaries=job_summaries,
                    fact_ledger=fact_ledger,
                    coverage_matrix=coverage_matrix,
                ),
            )
            report_v1.degraded_synthesis = True

        self.current_stage = "coverage_auditor"
        pre_patch_run_quality = self._assess_run_quality(
            fetched_sources=fetched_sources,
            evidence_items=evidence_items,
            fact_ledger=fact_ledger,
            report=report_v1,
            coverage_patch=CoveragePatch(coverage_score=float(report_v1.confidence_breakdown.get("coverage", 0.0))),
            degraded=degraded,
            coverage_matrix=coverage_matrix,
        )
        coverage_patch = await self._timed(
            "coverage_auditor",
            timings,
            self.coverage_auditor_agent.audit(
                original_query=research_question,
                planner_output=planner_output,
                search_headers=search_headers,
                evidence_items=evidence_items,
                fact_ledger=fact_ledger,
                report=report_v1,
                fetched_source_summary=getattr(self.source_fetcher, "summary", {}),
                provider_metrics=self._provider_metrics(),
                run_quality=pre_patch_run_quality,
            ),
        )

        # Phase 2.1: iterative gap-filling loop. Default MAX_RESEARCH_ITERATIONS=1
        # preserves current single-pass behavior; higher values run additional
        # research+fact-check+synthesis passes while the auditor reports gaps.
        iteration_history: list[dict[str, Any]] = []
        iterations_executed = 1
        max_iterations = max(1, int(getattr(config, "MAX_RESEARCH_ITERATIONS", 1) or 1))
        while (
            iterations_executed < max_iterations
            and coverage_patch.needs_new_search
            and coverage_patch.followup_research_jobs
        ):
            coverage_before = float(coverage_patch.coverage_score)
            prior_fact_count = len(fact_ledger.verified_facts) + len(fact_ledger.partial_facts)

            followup_jobs = coverage_patch.followup_research_jobs[:2]
            new_job_results, new_job_errors = await self._timed(
                f"research_jobs_iter_{iterations_executed + 1}",
                timings,
                self._run_research_jobs(research_question, followup_jobs),
            )
            errors.extend(new_job_errors)
            if new_job_errors:
                degraded = True

            for search_out, evidence_out in new_job_results:
                search_headers.extend(search_out.search_headers)
                evidence_items.extend(evidence_out.evidence_items)
                job_summaries.append(self._job_summary(search_out, evidence_out))
            fetched_sources = list(getattr(self, "_fetched_sources", []))

            fact_ledger = await self._timed(
                f"fact_checker_iter_{iterations_executed + 1}",
                timings,
                self.fact_checker_agent.check(
                    original_query=research_question,
                    planner_output=planner_output,
                    research_job_outputs=new_job_results,
                    search_headers=search_headers,
                    evidence_items=evidence_items,
                ),
            )
            coverage_matrix = build_coverage_matrix(planner_output, evidence_items, fact_ledger)

            try:
                report_v1 = await self._timed(
                    f"synthesizer_iter_{iterations_executed + 1}",
                    timings,
                    self._synthesize_report(
                        self.synthesizer_agent,
                        original_query=research_question,
                        planner_output=planner_output,
                        job_summaries=job_summaries,
                        fact_ledger=fact_ledger,
                        coverage_matrix=coverage_matrix,
                    ),
                )
            except SynthesisDegradedError as exc:
                errors.append({"stage": f"synthesizer_iter_{iterations_executed + 1}", "error": str(exc)})
                degraded = True
                report_v1 = report_v1  # keep prior report as the iteration fallback

            iteration_run_quality = self._assess_run_quality(
                fetched_sources=fetched_sources,
                evidence_items=evidence_items,
                fact_ledger=fact_ledger,
                report=report_v1,
                coverage_patch=coverage_patch,
                degraded=degraded,
                coverage_matrix=coverage_matrix,
            )
            coverage_patch = await self._timed(
                f"coverage_auditor_iter_{iterations_executed + 1}",
                timings,
                self.coverage_auditor_agent.audit(
                    original_query=research_question,
                    planner_output=planner_output,
                    search_headers=search_headers,
                    evidence_items=evidence_items,
                    fact_ledger=fact_ledger,
                    report=report_v1,
                    fetched_source_summary=getattr(self.source_fetcher, "summary", {}),
                    provider_metrics=self._provider_metrics(),
                    run_quality=iteration_run_quality,
                ),
            )

            new_fact_count = len(fact_ledger.verified_facts) + len(fact_ledger.partial_facts)
            iteration_history.append(
                {
                    "iteration": iterations_executed + 1,
                    "coverage_score_before": coverage_before,
                    "coverage_score_after": float(coverage_patch.coverage_score),
                    "new_facts_added": max(0, new_fact_count - prior_fact_count),
                    "needs_new_search": bool(coverage_patch.needs_new_search),
                }
            )
            iterations_executed += 1

        self.current_stage = "patch_applicator"
        patch_result = await self._timed(
            "patch_applicator",
            timings,
            self._apply_patch_async(report_v1, coverage_patch, fact_ledger),
        )

        self.current_stage = "complete"
        timings["total"] = round(perf_counter() - total_start, 6)
        run_quality = self._assess_run_quality(
            fetched_sources=fetched_sources,
            evidence_items=evidence_items,
            fact_ledger=fact_ledger,
            report=patch_result.report_v2,
            coverage_patch=coverage_patch,
            degraded=degraded,
            coverage_matrix=coverage_matrix,
        )
        provider_metrics = self._provider_metrics()
        provider_metrics["run_quality"] = run_quality

        return PipelineResult(
            research_question=research_question,
            planner_precontext=planner_output,
            search_headers=search_headers,
            fetched_sources=fetched_sources,
            fetched_source_summary=getattr(self.source_fetcher, "summary", {}),
            evidence_items=evidence_items,
            fact_ledger=fact_ledger,
            report=patch_result.report_v2,
            report_v1=patch_result.report_v1,
            report_v2=patch_result.report_v2,
            coverage_patch=coverage_patch,
            job_summaries=job_summaries,
            timings=timings,
            token_usage=self._collect_token_usage(),
            provider_metrics=provider_metrics,
            run_quality=run_quality,
            degraded=degraded,
            degraded_mode=degraded,
            errors=errors,
            iterations=iterations_executed,
            history=[{"degraded": degraded}, *iteration_history],
            uploads=upload_metadata,
        )

    async def _run_research_jobs(
        self,
        original_query: str,
        jobs: list[ResearchJob],
    ) -> tuple[list[tuple[JobSearchOutput, JobEvidenceOutput]], list[dict[str, Any]]]:
        search_results = await asyncio.gather(
            *[self._profiled(f"{job.job_id}:searcher", self.searcher_agent.run(job), {"job_id": job.job_id}) for job in jobs],
            return_exceptions=True,
        )
        errors: list[dict[str, Any]] = []
        successful_searches: list[JobSearchOutput] = []

        for job, result in zip(jobs, search_results):
            if isinstance(result, Exception):
                errors.append({"stage": "research_job", "job_id": job.job_id, "error": str(result)})
            else:
                successful_searches.append(result)

        all_headers = [header for search_output in successful_searches for header in search_output.search_headers]
        selected_headers = rank_search_headers(original_query, jobs, all_headers, limit=config.MAX_SEARCH_HEADERS_TOTAL)
        selected_header_ids = {header.result_id for header in selected_headers}
        limited_searches = [
            search_output.model_copy(
                update={"search_headers": [header for header in search_output.search_headers if header.result_id in selected_header_ids]}
            )
            for search_output in successful_searches
        ]

        fetched_sources = await self._profiled(
            "source_fetcher:global",
            self.source_fetcher.fetch_many(selected_headers),
            {"search_header_count": len(selected_headers)},
        )
        selected_sources = rank_fetched_sources(original_query, jobs, fetched_sources, selected_headers, limit=config.MAX_FETCHED_SOURCES_TOTAL)
        selected_sources = self._ensure_job_source_coverage(
            original_query,
            jobs,
            fetched_sources,
            selected_headers,
            selected_sources,
            config.MAX_FETCHED_SOURCES_TOTAL,
        )
        self._fetched_sources.extend(selected_sources)
        source_result_ids = {source.result_id for source in selected_sources}

        extraction_tasks = []
        extraction_searches = []
        for search_output in limited_searches:
            headers_for_job = [header for header in search_output.search_headers if header.result_id in source_result_ids]
            sources_for_job = [source for source in selected_sources if source.result_id in {header.result_id for header in headers_for_job}]
            limited_output = search_output.model_copy(update={"search_headers": headers_for_job})
            extraction_searches.append(limited_output)
            job = next(item for item in jobs if item.job_id == search_output.job_id)
            extraction_tasks.append(
                self._profiled(
                    f"{job.job_id}:evidence_extractor",
                    self.evidence_extractor_agent.extract(job, headers_for_job, sources_for_job),
                    {"job_id": job.job_id, "fetched_source_count": len(sources_for_job)},
                )
            )

        extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        job_results: list[tuple[JobSearchOutput, JobEvidenceOutput]] = []
        for search_output, result in zip(extraction_searches, extraction_results):
            if isinstance(result, Exception):
                errors.append({"stage": "evidence_extractor", "job_id": search_output.job_id, "error": str(result)})
            else:
                job_results.append((search_output, result))

        return job_results, errors

    async def _synthesize_report(
        self,
        synthesizer: Any,
        *,
        original_query: str,
        planner_output: PlannerOutput,
        job_summaries: list[dict[str, Any]],
        fact_ledger: FactLedger,
        coverage_matrix: dict[str, Any],
    ) -> ResearchReport:
        try:
            return await synthesizer.synthesize(
                original_query=original_query,
                planner_output=planner_output,
                job_summaries=job_summaries,
                fact_ledger=fact_ledger,
                coverage_matrix=coverage_matrix,
            )
        except TypeError as exc:
            if "coverage_matrix" not in str(exc):
                raise
            return await synthesizer.synthesize(
                original_query=original_query,
                planner_output=planner_output,
                job_summaries=job_summaries,
                fact_ledger=fact_ledger,
            )

    def _ensure_job_source_coverage(
        self,
        original_query: str,
        jobs: list[ResearchJob],
        fetched_sources: list[Any],
        selected_headers: list[SearchHeader],
        selected_sources: list[Any],
        limit: int,
    ) -> list[Any]:
        header_by_result = {header.result_id: header for header in selected_headers}
        selected = list(selected_sources)
        selected_ids = {source.result_id for source in selected}
        protected_ids: set[str] = set()

        for job in jobs:
            job_result_ids = {header.result_id for header in selected_headers if header.job_id == job.job_id}
            if not job_result_ids:
                continue
            if any(source.result_id in job_result_ids for source in selected):
                continue
            candidates = [
                source
                for source in fetched_sources
                if source.result_id in job_result_ids and source.result_id not in selected_ids and source.success and source.text
            ]
            if not candidates:
                continue
            job_headers = [header for header in selected_headers if header.result_id in {source.result_id for source in candidates}]
            best = rank_fetched_sources(original_query, [job], candidates, job_headers, limit=1)
            if best:
                selected.append(best[0])
                selected_ids.add(best[0].result_id)
                protected_ids.add(best[0].result_id)

        while len(selected) > limit:
            removable_index = self._removable_source_index(selected, protected_ids, header_by_result)
            if removable_index is None:
                break
            selected.pop(removable_index)
        return selected

    def _removable_source_index(self, sources: list[Any], protected_ids: set[str], header_by_result: dict[str, SearchHeader]) -> int | None:
        counts: dict[str, int] = {}
        for source in sources:
            job_id = header_by_result.get(source.result_id).job_id if header_by_result.get(source.result_id) else ""
            counts[job_id] = counts.get(job_id, 0) + 1
        for index in range(len(sources) - 1, -1, -1):
            source = sources[index]
            if source.result_id in protected_ids:
                continue
            job_id = header_by_result.get(source.result_id).job_id if header_by_result.get(source.result_id) else ""
            if counts.get(job_id, 0) > 1:
                return index
        for index in range(len(sources) - 1, -1, -1):
            if sources[index].result_id not in protected_ids:
                return index
        return None

    async def _run_single_job(self, job: ResearchJob) -> tuple[JobSearchOutput, JobEvidenceOutput]:
        search_output = await self._profiled(f"{job.job_id}:searcher", self.searcher_agent.run(job), {"job_id": job.job_id})
        fetched_sources = await self._profiled(
            f"{job.job_id}:source_fetcher",
            self.source_fetcher.fetch_many(search_output.search_headers),
            {"job_id": job.job_id, "search_header_count": len(search_output.search_headers)},
        )
        evidence_output = await self._profiled(
            f"{job.job_id}:evidence_extractor",
            self.evidence_extractor_agent.extract(job, search_output.search_headers, fetched_sources),
            {"job_id": job.job_id, "fetched_source_count": len(fetched_sources)},
        )
        self._fetched_sources.extend(fetched_sources)
        return search_output, evidence_output

    async def _apply_patch_async(
        self,
        report_v1: ResearchReport,
        coverage_patch: CoveragePatch,
        fact_ledger: FactLedger,
    ):
        try:
            return self.patch_applicator(report_v1, coverage_patch, fact_ledger)
        except PatchApplicationError:
            valid_operations = []
            for operation in coverage_patch.patch_operations:
                trial_patch = coverage_patch.model_copy(update={"patch_operations": [operation]})
                try:
                    self.patch_applicator(report_v1, trial_patch, fact_ledger)
                except PatchApplicationError:
                    continue
                valid_operations.append(operation)
            sanitized_patch = coverage_patch.model_copy(update={"patch_operations": valid_operations})
            return self.patch_applicator(report_v1, sanitized_patch, fact_ledger)

    async def _timed(self, name: str, timings: dict[str, float], awaitable):
        start = perf_counter()
        wall_start = datetime.now(timezone.utc)
        self._emit_progress("started", name, wall_start=wall_start)
        try:
            result = await awaitable
            timings[name] = round(perf_counter() - start, 6)
            wall_end = datetime.now(timezone.utc)
            self.profile_events.append(
                {
                    "operation": name,
                    "seconds": timings[name],
                    "wall_start": wall_start.isoformat(),
                    "wall_end": wall_end.isoformat(),
                    "ok": True,
                }
            )
            self._emit_progress("completed", name, seconds=timings[name], wall_start=wall_start, wall_end=wall_end)
            return result
        except Exception as exc:
            elapsed = round(perf_counter() - start, 6)
            wall_end = datetime.now(timezone.utc)
            timings[name] = elapsed
            self.profile_events.append(
                {
                    "operation": name,
                    "seconds": elapsed,
                    "wall_start": wall_start.isoformat(),
                    "wall_end": wall_end.isoformat(),
                    "ok": False,
                    "error": str(exc)[:500],
                }
            )
            self._emit_progress(
                "failed",
                name,
                seconds=elapsed,
                wall_start=wall_start,
                wall_end=wall_end,
                error=str(exc)[:500],
            )
            raise

    async def _profiled(self, operation: str, awaitable, metadata: dict[str, Any] | None = None):
        start = perf_counter()
        wall_start = datetime.now(timezone.utc)
        self._emit_progress("started", operation, wall_start=wall_start, **(metadata or {}))
        try:
            result = await awaitable
            elapsed = round(perf_counter() - start, 6)
            wall_end = datetime.now(timezone.utc)
            self.profile_events.append(
                {
                    "operation": operation,
                    "seconds": elapsed,
                    "wall_start": wall_start.isoformat(),
                    "wall_end": wall_end.isoformat(),
                    "ok": True,
                    **(metadata or {}),
                }
            )
            self._emit_progress("completed", operation, seconds=elapsed, wall_start=wall_start, wall_end=wall_end, **(metadata or {}))
            return result
        except Exception as exc:
            elapsed = round(perf_counter() - start, 6)
            wall_end = datetime.now(timezone.utc)
            self.profile_events.append(
                {
                    "operation": operation,
                    "seconds": elapsed,
                    "wall_start": wall_start.isoformat(),
                    "wall_end": wall_end.isoformat(),
                    "ok": False,
                    "error": str(exc)[:500],
                    **(metadata or {}),
                }
            )
            self._emit_progress(
                "failed",
                operation,
                seconds=elapsed,
                wall_start=wall_start,
                wall_end=wall_end,
                error=str(exc)[:500],
                **(metadata or {}),
            )
            raise

    def _emit_progress(self, event: str, operation: str, **payload: Any) -> None:
        if not self.progress_callback:
            return
        message = {
            "event": event,
            "operation": operation,
            "current_stage": getattr(self, "current_stage", ""),
            **payload,
        }
        for key in ("wall_start", "wall_end"):
            value = message.get(key)
            if isinstance(value, datetime):
                message[key] = value.isoformat()
        try:
            self.progress_callback(message)
        except Exception:
            # Progress reporting must never break the research run.
            return

    def _validate_planner_jobs(self, planner_output: PlannerOutput) -> None:
        if len(planner_output.research_jobs) != 2:
            raise ValueError("planner must produce exactly 2 research jobs")

    def _job_summary(self, search_output: JobSearchOutput, evidence_output: JobEvidenceOutput) -> dict[str, Any]:
        fallback_reasons = Counter(
            item.fallback_reason or "unspecified"
            for item in evidence_output.evidence_items
            if item.extraction_method == "deterministic_fallback"
        )
        return {
            "job_id": search_output.job_id,
            "search_coverage": search_output.search_coverage.model_dump(),
            "search_header_count": len(search_output.search_headers),
            "evidence_count": len(evidence_output.evidence_items),
            "extraction_failure_count": len(evidence_output.extraction_failures),
            "fallback_evidence_count": sum(fallback_reasons.values()),
            "fallback_reasons": dict(fallback_reasons),
        }

    def _assess_run_quality(
        self,
        *,
        fetched_sources: list[Any],
        evidence_items: list[EvidenceItem],
        fact_ledger: FactLedger,
        report: ResearchReport,
        coverage_patch: CoveragePatch,
        degraded: bool,
        coverage_matrix: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        successful_sources = [source for source in fetched_sources if getattr(source, "success", False)]
        fallback_items = [item for item in evidence_items if item.extraction_method == "deterministic_fallback"]
        llm_items = [item for item in evidence_items if item.extraction_method.startswith("llm")]
        snippet_items = [item for item in evidence_items if item.quote_location == "snippet"]
        fallback_reasons = Counter(item.fallback_reason or "unspecified" for item in fallback_items)

        evidence_count = len(evidence_items)
        successful_fetch_rate = len(successful_sources) / max(1, len(fetched_sources))
        fallback_rate = len(fallback_items) / max(1, evidence_count)
        llm_evidence_rate = len(llm_items) / max(1, evidence_count)
        snippet_rate = len(snippet_items) / max(1, evidence_count)
        average_source_quality = (
            sum(item.source_quality_score for item in evidence_items) / evidence_count
            if evidence_items
            else 0.0
        )

        verified_count = len(fact_ledger.verified_facts)
        partial_count = len(fact_ledger.partial_facts)
        unsupported_count = len(fact_ledger.unsupported_claims)
        contradiction_count = len(fact_ledger.contradictions)
        supported_fact_count = verified_count + partial_count

        source_score = (min(1.0, len(successful_sources) / 3) * 0.45) + (successful_fetch_rate * 0.25) + (average_source_quality * 0.30)
        evidence_score = (
            min(1.0, evidence_count / 5) * 0.35
            + llm_evidence_rate * 0.30
            + (1 - fallback_rate) * 0.20
            + (1 - snippet_rate) * 0.15
        )
        fact_penalty = min(0.45, (unsupported_count * 0.08) + (contradiction_count * 0.04))
        fact_score = max(0.0, min(1.0, supported_fact_count / 5) * 0.75 + (verified_count / max(1, supported_fact_count)) * 0.25 - fact_penalty)
        report_score = (float(report.confidence_score) * 0.55) + (float(coverage_patch.coverage_score) * 0.45)

        score = (source_score * 0.25) + (evidence_score * 0.35) + (fact_score * 0.25) + (report_score * 0.15)
        if degraded or getattr(report, "degraded_synthesis", False):
            score -= 0.15
        score = round(max(0.0, min(1.0, score)), 3)

        quality = {
            "score": score,
            "grade": self._quality_grade(score),
            "signals": {
                "fetched_source_count": len(fetched_sources),
                "successful_fetched_source_count": len(successful_sources),
                "successful_fetch_rate": round(successful_fetch_rate, 3),
                "evidence_count": evidence_count,
                "llm_evidence_count": len(llm_items),
                "fallback_evidence_count": len(fallback_items),
                "fallback_rate": round(fallback_rate, 3),
                "snippet_evidence_count": len(snippet_items),
                "snippet_rate": round(snippet_rate, 3),
                "average_source_quality": round(average_source_quality, 3),
                "verified_fact_count": verified_count,
                "partial_fact_count": partial_count,
                "unsupported_claim_count": unsupported_count,
                "contradiction_count": contradiction_count,
                "report_confidence": float(report.confidence_score),
                "coverage_score": float(coverage_patch.coverage_score),
                "degraded": degraded or getattr(report, "degraded_synthesis", False),
            },
            "fallback_reasons": dict(fallback_reasons),
        }
        if coverage_matrix:
            summary = coverage_matrix.get("summary", {})
            quality["coverage_matrix"] = coverage_matrix
            quality["evidence_quality_summary"] = {
                "average_evidence_fit": summary.get("average_evidence_fit", 0.0),
                "missing_requirements": summary.get("missing_requirements", []),
                "weak_requirements": summary.get("weak_requirements", []),
                "strong_requirements": summary.get("strong_requirements", []),
            }
        return quality

    def _quality_grade(self, score: float) -> str:
        if score >= 0.85:
            return "excellent"
        if score >= 0.70:
            return "good"
        if score >= 0.50:
            return "fair"
        return "weak"

    def _collect_token_usage(self) -> dict[str, int]:
        totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for component in [
            self.planner_agent,
            self.searcher_agent,
            self.evidence_extractor_agent,
            self.fact_checker_agent,
            self.synthesizer_agent,
            self.coverage_auditor_agent,
        ]:
            usage = getattr(component, "token_usage", None)
            if not usage and getattr(component, "llm_client", None):
                usage = getattr(component.llm_client, "token_usage", None)
            if isinstance(usage, dict):
                for key in totals:
                    totals[key] += int(usage.get(key, 0))
        return totals

    def _provider_metrics(self) -> dict[str, Any]:
        providers = [
            provider
            for provider in [
                self.llm_provider,
                self.planner_llm_provider,
                self.extraction_llm_provider,
                self.fact_checker_llm_provider,
                self.coverage_auditor_llm_provider,
                self.synthesizer_llm_provider,
            ]
            if provider
        ]
        unique_providers = []
        seen_ids = set()
        for provider in providers:
            if id(provider) in seen_ids:
                continue
            seen_ids.add(id(provider))
            unique_providers.append(provider)
        llm_calls = [call for provider in unique_providers for call in getattr(provider, "call_log", [])]
        return {
            "search_provider": getattr(self.search_provider, "provider", "composite"),
            "search_errors": getattr(self.search_provider, "last_errors", []),
            "search_events": getattr(self.search_provider, "search_events", []),
            "source_fetch": getattr(self.source_fetcher, "summary", {}),
            "source_fetch_events": getattr(self.source_fetcher, "fetch_events", []),
            "llm_provider": getattr(self.llm_provider, "provider", "none") if self.llm_provider else "none",
            "synthesizer_llm_provider": getattr(self.synthesizer_llm_provider, "provider", "none") if self.synthesizer_llm_provider else "none",
            "planner_llm_model": getattr(self.planner_llm_provider, "model", None),
            "extraction_llm_model": getattr(self.extraction_llm_provider, "model", None),
            "fact_checker_llm_model": getattr(self.fact_checker_llm_provider, "model", None),
            "coverage_auditor_llm_model": getattr(self.coverage_auditor_llm_provider, "model", None),
            "synthesizer_llm_model": getattr(self.synthesizer_llm_provider, "model", None),
            "llm_call_count": len(llm_calls),
            "llm_calls": llm_calls,
            "truncated_by_reasoning_count": sum(1 for call in llm_calls if call.get("truncated_by_reasoning")),
            "profile_events": self.profile_events,
        }

    def _safe_llm_provider(self, stage: str | None = None):
        try:
            return create_llm_provider(stage=stage)
        except Exception:
            return None

    def _synthesizer_provider(self, explicit_provider):
        if explicit_provider:
            return explicit_provider
        return self._safe_llm_provider(stage="synthesizer") or self.llm_provider

    def _stage_provider(self, stage: str, explicit_provider):
        """Return a stage-specific provider when a matching env is set, else reuse the shared provider.

        Phase 1.2: ``PLANNER_PROVIDER``/``PLANNER_MODEL`` style envs opt-in to a
        separate Gemini model per stage without changing default behavior.
        """
        if explicit_provider:
            return explicit_provider
        env_pair = {
            "planner": (config.PLANNER_PROVIDER, config.PLANNER_MODEL),
            "extraction": (config.EXTRACTION_PROVIDER, config.EXTRACTION_MODEL),
            "fact_checker": (config.FACT_CHECKER_PROVIDER, config.FACT_CHECKER_MODEL),
            "coverage_auditor": (config.COVERAGE_AUDITOR_PROVIDER, config.COVERAGE_AUDITOR_MODEL),
        }.get(stage, ("", ""))
        if not any(env_pair):
            # No override: share the top-level provider so today's behavior is preserved.
            return explicit_provider or self.llm_provider
        return self._safe_llm_provider(stage=stage) or self.llm_provider

    def _load_golden_result(self) -> PipelineResult:
        path = Path(self.golden_result_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return PipelineResult.model_validate(data)


def run_research(research_question: str) -> dict[str, Any]:
    """Synchronous compatibility wrapper for UI callers."""
    result = asyncio.run(SynapseResearchEngine().run(research_question))
    return result.model_dump()
