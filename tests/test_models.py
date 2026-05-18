import pytest
from pydantic import ValidationError

from backend.models import (
    CoveragePatch,
    EvidenceCriteria,
    EvidenceItem,
    FactLedger,
    PatchOperation,
    PipelineResult,
    PlannerPrecontext,
    ResearchJob,
    ResearchReport,
    SearchHeader,
)
from backend.validators import (
    require_source_quote,
    require_url,
    validate_fact_ids,
    validate_planner_citations,
    validate_report_has_citations,
)


def test_pipeline_models_accept_valid_schema():
    precontext = PlannerPrecontext(
        original_query="Compare AMD MI300X and NVIDIA H100 for inference",
        query_interpretation="Compare inference tradeoffs",
        precontext_claims=[
            {
                "claim": "AMD MI300X has high-memory HBM configuration.",
                "source_id": "src_001",
                "url": "https://example.com/mi300x",
                "support_level": "strong",
            }
        ],
        planning_risks=["Vendor benchmarks may not be comparable."],
        research_jobs=[
            {
                "job_id": "job_web",
                "job_name": "Industry evidence",
                "objective": "Find vendor and industry sources.",
                "search_queries": ["MI300X H100 inference benchmark"],
                "source_priorities": ["official", "benchmarks"],
                "must_answer": ["memory capacity", "throughput"],
            }
        ],
    )

    header = SearchHeader(
        result_id="res_001",
        job_id="job_web",
        query="MI300X H100 inference benchmark",
        title="Benchmark report",
        url="https://example.com/report",
        snippet="A benchmark result snippet.",
        rank=1,
    )
    evidence = EvidenceItem(
        evidence_id="ev_001",
        job_id="job_web",
        result_id=header.result_id,
        claim="MI300X has 192GB of HBM3 memory.",
        source_title=header.title,
        source_url=header.url,
        source_quote="The accelerator includes 192GB of HBM3 memory.",
    )
    ledger = FactLedger(
        verified_facts=[
            {
                "fact_id": "fact_001",
                "claim": evidence.claim,
                "status": "VERIFIED",
                "confidence": 0.9,
                "supporting_evidence_ids": [evidence.evidence_id],
                "source_urls": [evidence.source_url],
            }
        ]
    )
    report = ResearchReport(
        title="MI300X vs H100",
        answer_summary="MI300X offers larger memory capacity for some inference workloads.",
        sections=[
            {
                "section_id": "sec_001",
                "heading": "Memory",
                "content": "MI300X has 192GB HBM3.",
                "used_fact_ids": ["fact_001"],
                "citations": ["https://example.com/report"],
            }
        ],
        key_findings=[
            {
                "finding": "MI300X has 192GB HBM3.",
                "fact_ids": ["fact_001"],
                "citations": ["https://example.com/report"],
                "confidence": 0.9,
            }
        ],
        confidence_score=0.8,
        confidence_breakdown={"verified_ratio": 1.0, "coverage": 0.6},
        used_fact_ids=["fact_001"],
    )
    patch = CoveragePatch(
        coverage_score=0.95,
        patch_operations=[
            PatchOperation(
                op="add_caveat",
                target_section_id="sec_001",
                text="Benchmarks vary by workload.",
                fact_ids=["fact_001"],
                contradiction_ids=[],
                result_ids=[],
                reason="Add benchmark caveat.",
            )
        ],
    )

    result = PipelineResult(
        research_question=precontext.original_query,
        planner_precontext=precontext,
        search_headers=[header],
        evidence_items=[evidence],
        fact_ledger=ledger,
        report=report,
        coverage_patch=patch,
    )

    dumped = result.model_dump()
    assert dumped["planner_precontext"]["research_jobs"][0]["job_id"] == "job_web"
    assert dumped["report"]["sections"][0]["citations"] == ["https://example.com/report"]
    assert isinstance(precontext.evidence_criteria, EvidenceCriteria)
    assert evidence.target == ""
    assert evidence.dimension == ""
    assert evidence.evidence_fit_score == 0.0


def test_models_reject_missing_urls_and_quotes():
    with pytest.raises(ValidationError):
        SearchHeader(
            result_id="res_001",
            job_id="job_web",
            query="query",
            title="title",
            url="not-a-url",
            snippet="snippet",
            rank=1,
        )

    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_001",
            job_id="job_web",
            result_id="res_001",
            claim="A claim",
            source_title="Source",
            source_url="https://example.com/source",
            source_quote="",
        )


def test_validation_helpers_raise_clear_errors():
    assert require_url("https://example.com") == "https://example.com"
    assert require_source_quote(" quoted evidence ") == "quoted evidence"

    with pytest.raises(ValueError, match="url"):
        require_url("ftp://example.com")

    with pytest.raises(ValueError, match="source_quote"):
        require_source_quote(" ")

    with pytest.raises(ValueError, match="precontext"):
        validate_planner_citations([])

    with pytest.raises(ValueError, match="unknown fact"):
        validate_fact_ids({"fact_001"}, ["fact_002"], context="report")

    with pytest.raises(ValueError, match="citations"):
        ResearchReport(
            title="No citations",
            answer_summary="Summary",
            sections=[
                {
                    "section_id": "sec_001",
                    "heading": "Findings",
                    "content": "Content",
                    "used_fact_ids": ["fact_001"],
                    "citations": [],
                }
            ],
            key_findings=[],
            confidence_score=0.5,
            confidence_breakdown={},
            used_fact_ids=["fact_001"],
        )
