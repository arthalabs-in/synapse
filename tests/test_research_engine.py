import asyncio
import json
from pathlib import Path

from backend.models import (
    CoveragePatch,
    EvidenceItem,
    FactLedger,
    FetchedSource,
    JobEvidenceOutput,
    JobSearchOutput,
    PipelineResult,
    PlannerOutput,
    ResearchJob,
    ResearchReport,
    SearchCoverage,
    SearchHeader,
    VerifiedFact,
)
from backend.patch_applicator import apply_patch
from backend.research_engine import SynapseResearchEngine
from agents.synthesizer import SynthesisDegradedError


def test_full_pipeline_with_mocked_agents():
    engine = make_engine()

    result = asyncio.run(engine.run("Compare GPUs"))

    assert isinstance(result, PipelineResult)
    assert result.degraded is False
    assert len(result.job_summaries) == 2
    assert result.report_v1.report_id == "report_v1"
    assert result.report_v2.report_id == "report_v2"
    assert result.report.report_id == "report_v2"
    assert result.coverage_patch.patch_operations


def test_one_job_failure_still_returns_degraded_result():
    engine = make_engine(searcher=FakeSearcher(fail_job_id="job_b"))

    result = asyncio.run(engine.run("Compare GPUs"))

    assert result.degraded is True
    assert len(result.job_summaries) == 1
    assert result.errors
    assert result.report_v2 is not None


def test_demo_mode_loads_fixture():
    golden = make_pipeline_result().model_dump(mode="json")
    fixture = Path("tests/fixtures/golden_pipeline_result_test.json")
    fixture.parent.mkdir(exist_ok=True)
    fixture.write_text(json.dumps(golden), encoding="utf-8")
    engine = make_engine(demo_mode=True, golden_result_path=str(fixture))

    result = asyncio.run(engine.run("Ignored in demo"))

    assert result.research_question == "Compare GPUs"
    assert result.history == [{"mode": "demo"}]


def test_timings_are_included():
    result = asyncio.run(make_engine().run("Compare GPUs"))

    assert {"planner", "research_jobs", "fact_checker", "synthesizer", "coverage_auditor", "patch_applicator", "total"} <= set(result.timings)
    assert all(value >= 0 for value in result.timings.values())


def test_progress_callback_receives_stage_and_operation_events():
    events = []
    engine = make_engine(progress_callback=events.append)

    asyncio.run(engine.run("Compare GPUs"))

    operations = [event["operation"] for event in events]
    assert "planner" in operations
    assert "job_a:searcher" in operations
    assert "source_fetcher:global" in operations
    assert "job_a:evidence_extractor" in operations
    assert "fact_checker" in operations
    assert any(event["event"] == "started" and event["operation"] == "planner" for event in events)
    assert any(event["event"] == "completed" and event["operation"] == "patch_applicator" for event in events)


def test_global_source_selection_keeps_sources_for_each_successful_job(monkeypatch):
    monkeypatch.setattr("backend.research_engine.config.MAX_FETCHED_SOURCES_TOTAL", 4)
    engine = make_engine(searcher=SkewedSearcher())

    result = asyncio.run(engine.run("Compare GPUs"))

    by_job = {summary["job_id"]: summary for summary in result.job_summaries}
    assert by_job["job_a"]["search_header_count"] >= 1
    assert by_job["job_b"]["search_header_count"] >= 1


def test_default_synthesizer_receives_llm_provider():
    provider = object()

    engine = SynapseResearchEngine(
        planner_agent=FakePlanner(),
        searcher_agent=FakeSearcher(),
        evidence_extractor_agent=FakeExtractor(),
        fact_checker_agent=FakeFactChecker(),
        coverage_auditor_agent=FakeAuditor(),
        source_fetcher=FakeSourceFetcher(),
        patch_applicator=apply_patch,
        llm_provider=provider,
        demo_mode=False,
    )

    assert engine.synthesizer_agent.llm_provider is provider


def test_engine_records_degraded_when_synthesis_empty_visible_content():
    engine = make_engine(synthesizer=FailingSynthesizer())

    result = asyncio.run(engine.run("Compare GPUs"))

    assert result.degraded is True
    assert any(error.get("stage") == "synthesizer" for error in result.errors)
    assert result.report_v1.degraded_synthesis is True
    assert result.report_v1.sections[0].section_id == "sec_verified"


def test_pipeline_result_includes_run_quality_and_fallback_reason_counts():
    result = asyncio.run(make_engine(extractor=FallbackExtractor()).run("Compare GPUs"))

    assert result.run_quality["signals"]["evidence_count"] == 2
    assert result.run_quality["signals"]["fallback_evidence_count"] == 2
    assert result.run_quality["fallback_reasons"] == {"llm_returned_no_accepted_evidence: test": 2}
    assert result.run_quality["grade"] in {"fair", "weak"}
    assert result.provider_metrics["run_quality"] == result.run_quality


def make_engine(searcher=None, extractor=None, synthesizer=None, demo_mode=False, golden_result_path=None, progress_callback=None):
    return SynapseResearchEngine(
        planner_agent=FakePlanner(),
        searcher_agent=searcher or FakeSearcher(),
        evidence_extractor_agent=extractor or FakeExtractor(),
        fact_checker_agent=FakeFactChecker(),
        synthesizer_agent=synthesizer or FakeSynthesizer(),
        coverage_auditor_agent=FakeAuditor(),
        source_fetcher=FakeSourceFetcher(),
        patch_applicator=apply_patch,
        demo_mode=demo_mode,
        golden_result_path=golden_result_path,
        progress_callback=progress_callback,
    )


class FakePlanner:
    token_usage = {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}

    async def plan(self, query):
        return make_planner()


class FakeSearcher:
    def __init__(self, fail_job_id=None):
        self.fail_job_id = fail_job_id

    async def run(self, job):
        if job.job_id == self.fail_job_id:
            raise RuntimeError("search failed")
        header = make_header(job.job_id)
        return JobSearchOutput(
            job_id=job.job_id,
            search_headers=[header],
            search_coverage=SearchCoverage(queries_run=1, results_found=1),
        )


class SkewedSearcher:
    async def run(self, job):
        headers = []
        for index in range(6):
            title = (
                f"Compare GPUs memory official source {index}"
                if job.job_id == "job_a"
                else f"Lower-overlap deployment source {index}"
            )
            headers.append(
                SearchHeader(
                    result_id=f"res_{job.job_id}_{index}",
                    job_id=job.job_id,
                    query=job.search_queries[0],
                    title=title,
                    url=f"https://example.com/{job.job_id}/{index}",
                    snippet=title,
                    rank=index + 1,
                    source_type_guess="official",
                )
            )
        return JobSearchOutput(
            job_id=job.job_id,
            search_headers=headers,
            search_coverage=SearchCoverage(queries_run=1, results_found=len(headers)),
        )


class FakeExtractor:
    async def extract(self, job, search_headers, fetched_sources=None):
        header = search_headers[0]
        return JobEvidenceOutput(
            job_id=job.job_id,
            evidence_items=[],
            extraction_failures=[],
        )


class FallbackExtractor:
    async def extract(self, job, search_headers, fetched_sources=None):
        header = search_headers[0]
        source = fetched_sources[0]
        return JobEvidenceOutput(
            job_id=job.job_id,
            evidence_items=[
                EvidenceItem(
                    evidence_id=f"ev_{job.job_id}_001",
                    job_id=job.job_id,
                    result_id=header.result_id,
                    fetched_source_id=source.source_id,
                    claim="Official product information about GPU memory.",
                    source_title=header.title,
                    source_url=header.url,
                    source_quote="Official product information about GPU memory.",
                    quote_location="page",
                    source_type=source.source_type,
                    source_quality_score=source.source_quality_score,
                    extraction_method="deterministic_fallback",
                    fallback_reason="llm_returned_no_accepted_evidence: test",
                    relevance_to_query=0.5,
                )
            ],
            extraction_failures=[],
        )


class FakeSourceFetcher:
    summary = {"fetched_http_count": 2, "fetched_camofox_count": 0, "arxiv_metadata_count": 0, "failed_count": 0}

    async def fetch_many(self, search_headers):
        page_text = (
            "Official product information about GPU memory, throughput, software support, "
            "deployment constraints, and practical inference tradeoffs for production workloads. "
        ) * 4
        return [
            FetchedSource(
                source_id=f"src_{header.result_id}",
                result_id=header.result_id,
                url=header.url,
                canonical_url=header.url,
                title=header.title,
                domain="amd.com" if "mi300x" in header.url else "nvidia.com",
                text=page_text,
                source_type="official",
                source_quality_score=0.9,
                provider="http",
                fetch_status="fetched_http",
                success=True,
            )
            for header in search_headers
        ]


class FakeFactChecker:
    async def check(self, original_query, planner_output, research_job_outputs, search_headers, evidence_items):
        return make_ledger()


class FakeSynthesizer:
    async def synthesize(self, original_query, planner_output, job_summaries, fact_ledger):
        return make_report()


class FailingSynthesizer:
    async def synthesize(self, original_query, planner_output, job_summaries, fact_ledger):
        raise SynthesisDegradedError("empty visible content")


class FakeAuditor:
    async def audit(
        self,
        original_query,
        planner_output,
        search_headers,
        evidence_items,
        fact_ledger,
        report,
        fetched_source_summary=None,
        provider_metrics=None,
        run_quality=None,
    ):
        return CoveragePatch(
            coverage_score=1.0,
            revision_brief={
                "fetched_source_summary": fetched_source_summary or {},
                "run_quality": run_quality or {},
            },
            patch_operations=[
                {
                    "op": "add",
                    "target_section_id": "sec_verified",
                    "text": "H100 has 80GB memory.",
                    "fact_ids": ["fact_002"],
                    "reason": "Add missing fact.",
                }
            ],
        )


def make_pipeline_result():
    planner = make_planner()
    ledger = make_ledger()
    report = make_report()
    patch = CoveragePatch(coverage_score=1.0)
    return PipelineResult(
        research_question="Compare GPUs",
        planner_precontext=planner,
        fact_ledger=ledger,
        report=report,
        report_v1=report,
        report_v2=report,
        coverage_patch=patch,
        history=[{"mode": "demo"}],
    )


def make_planner():
    jobs = [
        ResearchJob(
            job_id="job_a",
            job_name="Job A",
            objective="Find MI300X facts.",
            search_queries=["mi300x memory"],
            source_priorities=["official"],
            must_answer=["memory"],
        ),
        ResearchJob(
            job_id="job_b",
            job_name="Job B",
            objective="Find H100 facts.",
            search_queries=["h100 memory"],
            source_priorities=["official"],
            must_answer=["memory"],
        ),
    ]
    return PlannerOutput(
        original_query="Compare GPUs",
        query_interpretation="Compare GPU memory.",
        precontext_claims=[
            {"claim": "Memory is relevant.", "source_id": "src_001", "url": "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"}
        ],
        research_jobs=jobs,
        coverage_checklist=["memory"],
    )


def make_header(job_id):
    return SearchHeader(
        result_id=f"res_{job_id}",
        job_id=job_id,
        query="memory",
        title="Source",
        url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"
        if job_id == "job_a"
        else "https://www.nvidia.com/en-us/data-center/h100/",
        snippet="Snippet.",
        rank=1,
        source_type_guess="official",
    )


def make_ledger():
    return FactLedger(
        verified_facts=[
            make_fact("fact_001", "MI300X has 192GB memory.", ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"]),
            make_fact("fact_002", "H100 has 80GB memory.", ["https://www.nvidia.com/en-us/data-center/h100/"]),
        ],
        source_quality_summary={"official": 2},
    )


def make_report():
    fact = make_fact("fact_001", "MI300X has 192GB memory.", ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"])
    return ResearchReport(
        report_id="report_v1",
        title="Compare GPUs",
        answer_summary=fact.claim,
        sections=[
            {
                "section_id": "sec_verified",
                "heading": "Verified",
                "content": fact.claim,
                "used_fact_ids": [fact.fact_id],
                "citations": fact.source_urls,
            }
        ],
        key_findings=[
            {
                "finding": fact.claim,
                "fact_ids": [fact.fact_id],
                "citations": fact.source_urls,
                "confidence": fact.confidence,
            }
        ],
        confidence_score=0.5,
        confidence_breakdown={"coverage": 0.5},
        used_fact_ids=[fact.fact_id],
        sources=fact.source_urls,
    )


def make_fact(fact_id, claim, urls):
    return VerifiedFact(
        fact_id=fact_id,
        claim=claim,
        status="VERIFIED",
        confidence=0.9,
        supporting_evidence_ids=[fact_id.replace("fact", "ev")],
        source_urls=urls,
    )
