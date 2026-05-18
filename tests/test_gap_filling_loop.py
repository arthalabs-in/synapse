"""Phase 2.1: integration tests for the MAX_RESEARCH_ITERATIONS gap-filling loop."""

import asyncio

from backend.models import (
    CoveragePatch,
    EvidenceItem,
    FactLedger,
    FetchedSource,
    JobEvidenceOutput,
    JobSearchOutput,
    PlannerOutput,
    ResearchJob,
    SearchCoverage,
    SearchHeader,
    VerifiedFact,
)
from backend.patch_applicator import apply_patch
from backend.research_engine import SynapseResearchEngine


def _header(job_id: str, suffix: str = "") -> SearchHeader:
    return SearchHeader(
        result_id=f"res_{job_id}{suffix}",
        job_id=job_id,
        query="q",
        title=f"Source {job_id}{suffix}",
        url=f"https://example-real.org/{job_id}{suffix}".replace("example-real.org", "www.amd.com"),
        snippet="Snippet.",
        rank=1,
        source_type_guess="official",
    )


class _Planner:
    token_usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

    async def plan(self, query):
        jobs = [
            ResearchJob(
                job_id="job_a",
                job_name="Job A",
                objective="first angle",
                search_queries=["q"],
                source_priorities=["official"],
                must_answer=["x"],
            ),
            ResearchJob(
                job_id="job_b",
                job_name="Job B",
                objective="second angle",
                search_queries=["q"],
                source_priorities=["official"],
                must_answer=["x"],
            ),
        ]
        return PlannerOutput(
            original_query=query,
            query_interpretation="plan",
            precontext_claims=[
                {
                    "claim": "seed",
                    "source_id": "src_001",
                    "url": "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
                }
            ],
            research_jobs=jobs,
            coverage_checklist=["x"],
        )


class _Searcher:
    async def run(self, job):
        return JobSearchOutput(
            job_id=job.job_id,
            search_headers=[_header(job.job_id)],
            search_coverage=SearchCoverage(queries_run=1, results_found=1),
        )


class _Extractor:
    async def extract(self, job, search_headers, fetched_sources=None):
        return JobEvidenceOutput(
            job_id=job.job_id,
            evidence_items=[],
            extraction_failures=[],
        )


class _SourceFetcher:
    summary = {"fetched_http_count": 2, "fetched_camofox_count": 0, "arxiv_metadata_count": 0, "failed_count": 0}

    async def fetch_many(self, search_headers):
        return [
            FetchedSource(
                source_id=f"src_{header.result_id}",
                result_id=header.result_id,
                url=header.url,
                title=header.title,
                text="Text for page. " * 20,
                source_type="official",
                source_quality_score=0.9,
                fetch_status="fetched_http",
                provider="http",
                success=True,
            )
            for header in search_headers
        ]


class _FactChecker:
    """Each call returns a ledger whose size grows with the number of calls."""

    def __init__(self):
        self.calls = 0

    async def check(self, original_query, planner_output, research_job_outputs, search_headers, evidence_items):
        self.calls += 1
        facts = [
            VerifiedFact(
                fact_id=f"fact_{index}",
                claim=f"Claim {index}",
                status="VERIFIED",
                confidence=0.9,
                supporting_evidence_ids=[f"ev_{index}"],
                source_urls=["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"],
            )
            for index in range(self.calls)
        ]
        return FactLedger(verified_facts=facts, source_quality_summary={"official": self.calls})


class _Synthesizer:
    async def synthesize(self, original_query, planner_output, job_summaries, fact_ledger):
        from backend.models import ResearchReport

        used = [fact.fact_id for fact in fact_ledger.verified_facts]
        sources = list({url for fact in fact_ledger.verified_facts for url in fact.source_urls})
        return ResearchReport(
            report_id="report_v1",
            title="Title",
            answer_summary="Summary.",
            sections=[
                {
                    "section_id": "sec_verified",
                    "heading": "Verified",
                    "content": "Verified content.",
                    "used_fact_ids": used or ["fact_0"],
                    "citations": sources or ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"],
                }
            ],
            confidence_score=0.5,
            confidence_breakdown={"coverage": 0.5},
            used_fact_ids=used or ["fact_0"],
            sources=sources or ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"],
        )


class _ToggleAuditor:
    """First call: needs_new_search=True with one follow-up job. Second call: done."""

    def __init__(self):
        self.calls = 0

    async def audit(self, **kwargs):
        self.calls += 1
        needs_new = self.calls == 1
        followup_jobs = []
        if needs_new:
            followup_jobs = [
                ResearchJob(
                    job_id="job_followup",
                    job_name="Followup",
                    objective="fill the gap",
                    search_queries=["more"],
                    source_priorities=["official"],
                    must_answer=["gap"],
                )
            ]
        fact_ledger = kwargs.get("fact_ledger")
        first_fact = fact_ledger.verified_facts[0] if fact_ledger and fact_ledger.verified_facts else None
        patch_ops = []
        if first_fact:
            patch_ops.append(
                {
                    "op": "add",
                    "target_section_id": "sec_verified",
                    "text": first_fact.claim,
                    "fact_ids": [first_fact.fact_id],
                    "reason": "gap-fill",
                }
            )
        return CoveragePatch(
            coverage_score=0.4 if needs_new else 0.9,
            needs_new_search=needs_new,
            followup_research_jobs=followup_jobs,
            patch_operations=patch_ops,
        )


class _StaticAuditor:
    async def audit(self, **kwargs):
        fact_ledger = kwargs.get("fact_ledger")
        first_fact = fact_ledger.verified_facts[0] if fact_ledger and fact_ledger.verified_facts else None
        patch_ops = []
        if first_fact:
            patch_ops.append(
                {
                    "op": "add",
                    "target_section_id": "sec_verified",
                    "text": first_fact.claim,
                    "fact_ids": [first_fact.fact_id],
                    "reason": "none",
                }
            )
        return CoveragePatch(coverage_score=0.9, needs_new_search=False, patch_operations=patch_ops)


def _make_engine(auditor, max_iterations, monkeypatch):
    monkeypatch.setattr("backend.research_engine.config.MAX_RESEARCH_ITERATIONS", max_iterations)
    return SynapseResearchEngine(
        planner_agent=_Planner(),
        searcher_agent=_Searcher(),
        evidence_extractor_agent=_Extractor(),
        fact_checker_agent=_FactChecker(),
        synthesizer_agent=_Synthesizer(),
        coverage_auditor_agent=auditor,
        source_fetcher=_SourceFetcher(),
        patch_applicator=apply_patch,
        demo_mode=False,
    )


def test_gap_filling_loop_runs_two_iterations_when_needed(monkeypatch):
    auditor = _ToggleAuditor()
    engine = _make_engine(auditor, max_iterations=3, monkeypatch=monkeypatch)

    result = asyncio.run(engine.run("test query"))

    assert result.iterations == 2
    iter_entries = [h for h in result.history if h.get("iteration")]
    assert len(iter_entries) == 1, "history should record exactly one follow-up iteration"
    assert iter_entries[0]["iteration"] == 2
    assert iter_entries[0]["coverage_score_before"] == 0.4
    assert iter_entries[0]["coverage_score_after"] == 0.9
    assert iter_entries[0]["new_facts_added"] >= 1
    # Engine must have run two full audit passes plus the follow-up research job.
    assert auditor.calls == 2


def test_gap_filling_loop_respects_max_iterations_one_default(monkeypatch):
    auditor = _ToggleAuditor()
    engine = _make_engine(auditor, max_iterations=1, monkeypatch=monkeypatch)

    result = asyncio.run(engine.run("test query"))

    assert result.iterations == 1
    assert auditor.calls == 1, "default MAX_RESEARCH_ITERATIONS=1 must not iterate"
    assert not any(h.get("iteration") for h in result.history)


def test_gap_filling_loop_stops_when_auditor_reports_done(monkeypatch):
    engine = _make_engine(_StaticAuditor(), max_iterations=3, monkeypatch=monkeypatch)

    result = asyncio.run(engine.run("test query"))

    assert result.iterations == 1, "no iteration should fire when needs_new_search is False on pass 1"
