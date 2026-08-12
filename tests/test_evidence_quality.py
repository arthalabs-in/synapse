from backend.evidence_quality import (
    build_coverage_matrix,
    build_evidence_criteria,
    infer_query_dimensions,
    infer_query_targets,
    score_source_fitness,
)
from backend.models import EvidenceItem, FactLedger, FetchedSource, PlannerPrecontext, ResearchJob


QUERY = (
    "For a small nonprofit with limited technical staff, compare a general-purpose chatbot, "
    "a retrieval-augmented chatbot, and a source-audited research workflow for drafting grant "
    "proposals and policy briefs. Evaluate reliability, citation quality, implementation cost, "
    "staff usability, privacy risk, and long-term maintainability."
)


def test_query_intent_infers_targets_and_dimensions():
    assert "retrieval-augmented chatbot" in infer_query_targets(QUERY)
    dimensions = infer_query_dimensions(QUERY)
    assert "citation quality" in dimensions
    assert "privacy risk" in dimensions
    assert "maintainability" in dimensions


def test_source_fitness_penalizes_unrelated_domain():
    planner = make_planner()
    weak = make_source(
        "autonomous vehicles perception benchmark camera sensor accuracy lane detection",
        "Autonomous vehicle perception benchmark",
    )
    strong = make_source(
        "RAG privacy risks citation grounding grant proposal workflow nonprofit staff maintenance cost",
        "RAG privacy and source-grounded nonprofit research workflow",
    )

    weak_score = score_source_fitness(QUERY, planner, weak)
    strong_score = score_source_fitness(QUERY, planner, strong)

    assert strong_score["score"] > weak_score["score"]
    assert any("weakly related" in note or "narrow" in note for note in weak_score["notes"])


def test_coverage_matrix_marks_missing_and_strong_cells():
    planner = make_planner()
    evidence = EvidenceItem(
        evidence_id="ev_1",
        job_id="job_a",
        result_id="res_1",
        claim="RAG systems can expose sensitive knowledge-base data.",
        source_title="RAG privacy paper",
        source_url="https://example.com/rag-privacy",
        source_quote="RAG systems can expose sensitive knowledge-base data.",
        target="retrieval-augmented chatbot",
        dimension="privacy risk",
        evidence_fit_score=0.9,
    )
    ledger = FactLedger(
        partial_facts=[
            {
                "fact_id": "fact_1",
                "claim": evidence.claim,
                "status": "PARTIAL",
                "confidence": 0.8,
                "supporting_evidence_ids": ["ev_1"],
                "source_urls": ["https://example.com/rag-privacy"],
            }
        ]
    )

    matrix = build_coverage_matrix(planner, [evidence], ledger)

    summary = matrix["summary"]
    assert summary["strong_requirements"]
    assert summary["missing_requirements"]
    assert matrix["matrix"]["retrieval-augmented chatbot"]["privacy risk"]["fact_ids"] == ["fact_1"]


def make_planner():
    job = ResearchJob(
        job_id="job_a",
        job_name="Compare options",
        objective=QUERY,
        search_queries=[QUERY],
        source_priorities=["official", "paper", "docs"],
        must_answer=infer_query_dimensions(QUERY),
    )
    planner = PlannerPrecontext(
        original_query=QUERY,
        query_interpretation=QUERY,
        precontext_claims=[],
        research_jobs=[job],
        coverage_checklist=infer_query_dimensions(QUERY),
    )
    planner.evidence_criteria = build_evidence_criteria(QUERY, planner)
    return planner


def make_source(text: str, title: str):
    return FetchedSource(
        source_id="src_1",
        result_id="res_1",
        url="https://example.com/source",
        title=title,
        domain="example.com",
        text=text * 30,
        source_type="paper",
        source_quality_score=0.8,
        provider="http",
        fetch_status="fetched_http",
        success=True,
    )
