import pytest

from backend.models import Contradiction, CoveragePatch, FactLedger, PatchOperation, ResearchReport, VerifiedFact
from backend.patch_applicator import PatchApplicationError, apply_patch


def test_add_operation_inserts_text_into_target_section():
    report = make_report([make_fact("fact_001", "MI300X has 192GB memory.")])
    fact = make_fact("fact_002", "H100 has 80GB memory.", ["https://example.com/h100"])
    ledger = FactLedger(verified_facts=[make_fact("fact_001", "MI300X has 192GB memory."), fact])
    patch = CoveragePatch(
        coverage_score=0.8,
        patch_operations=[
            PatchOperation(
                op="add",
                target_section_id="sec_verified",
                text="H100 has 80GB memory.",
                fact_ids=["fact_002"],
                reason="Add missing verified fact.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    section = result.report_v2.sections[0]
    assert "H100 has 80GB memory." in section.content
    assert "fact_002" in section.used_fact_ids
    assert "https://example.com/h100" in section.citations
    assert result.report_v1.report_id == "report_v1"
    assert result.report_v2.report_id == "report_v2"


def test_weaken_operation_changes_overstrong_wording():
    fact = make_fact("fact_001", "MI300X may perform well for some inference workloads.", status="PARTIAL")
    ledger = FactLedger(partial_facts=[fact])
    report = make_report(
        [fact],
        content="MI300X is always the fastest option for inference workloads.",
    )
    patch = CoveragePatch(
        coverage_score=0.7,
        patch_operations=[
            PatchOperation(
                op="weaken",
                target_section_id="sec_verified",
                text="MI300X may perform well for some inference workloads.",
                fact_ids=["fact_001"],
                reason="Partial evidence requires weaker wording.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    assert "always the fastest" not in result.report_v2.sections[0].content
    assert "may perform well" in result.report_v2.sections[0].content


def test_applied_operation_preserves_ui_edit_metadata():
    fact = make_fact("fact_001", "MI300X may perform well for some inference workloads.", status="PARTIAL")
    ledger = FactLedger(partial_facts=[fact])
    report = make_report(
        [fact],
        content="MI300X is always the fastest option for inference workloads.",
    )
    patch = CoveragePatch(
        coverage_score=0.7,
        patch_operations=[
            PatchOperation(
                edit_id="edit_001",
                op="weaken",
                target_section_id="sec_verified",
                target_path="sections[section_id=sec_verified].content",
                edit_label="Weaken inference claim",
                original_text="MI300X is always the fastest option for inference workloads.",
                replacement_text="MI300X may perform well for some inference workloads.",
                text="MI300X may perform well for some inference workloads.",
                fact_ids=["fact_001"],
                reason="Partial evidence needs less certain wording.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    operation = result.applied_operations[0]
    assert operation.edit_id == "edit_001"
    assert operation.target_path == "sections[section_id=sec_verified].content"
    assert operation.edit_label == "Weaken inference claim"
    assert operation.original_text == "MI300X is always the fastest option for inference workloads."
    assert operation.replacement_text == "MI300X may perform well for some inference workloads."
    assert operation.reason == "Partial evidence needs less certain wording."


def test_operation_with_original_and_replacement_text_rewrites_target_span():
    fact = make_fact("fact_001", "MI300X may perform well for some inference workloads.", status="PARTIAL")
    ledger = FactLedger(partial_facts=[fact])
    report = make_report(
        [fact],
        content="MI300X is always the fastest option for inference workloads. Keep this context.",
    )
    patch = CoveragePatch(
        coverage_score=0.7,
        patch_operations=[
            PatchOperation(
                edit_id="edit_001",
                op="weaken",
                target_section_id="sec_verified",
                target_path="sections[section_id=sec_verified].content",
                original_text="MI300X is always the fastest option for inference workloads.",
                replacement_text="MI300X may perform well for some inference workloads.",
                text="MI300X may perform well for some inference workloads.",
                fact_ids=["fact_001"],
                reason="Replace only the unsupported span.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    assert result.report_v2.sections[0].content == "MI300X may perform well for some inference workloads. Keep this context."


def test_invalid_fact_id_patch_is_rejected():
    report = make_report([make_fact("fact_001", "MI300X has 192GB memory.")])
    ledger = FactLedger(verified_facts=[make_fact("fact_001", "MI300X has 192GB memory.")])
    patch = CoveragePatch(
        coverage_score=0.8,
        patch_operations=[
            PatchOperation(
                op="add",
                target_section_id="sec_verified",
                text="Unknown fact.",
                fact_ids=["fact_missing"],
                reason="Bad patch.",
            )
        ],
    )

    with pytest.raises(PatchApplicationError, match="unknown fact_id"):
        apply_patch(report, patch, ledger)


def test_confidence_changes_after_valid_patch():
    report = make_report([make_fact("fact_001", "MI300X has 192GB memory.")])
    fact = make_fact("fact_002", "H100 has 80GB memory.", ["https://example.com/h100"])
    ledger = FactLedger(verified_facts=[make_fact("fact_001", "MI300X has 192GB memory."), fact])
    patch = CoveragePatch(
        coverage_score=1.0,
        patch_operations=[
            PatchOperation(
                op="add",
                target_section_id="sec_verified",
                text="H100 has 80GB memory.",
                fact_ids=["fact_002"],
                reason="Add missing verified fact.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    assert result.report_v2.confidence_score != report.confidence_score
    assert result.report_v2.confidence_breakdown["coverage"] > report.confidence_breakdown["coverage"]


def test_contradiction_patch_attaches_related_fact_citations():
    fact_a = make_fact("fact_001", "Gemini grounding uses live web content.", ["https://example.com/grounding"])
    fact_b = make_fact("fact_002", "Gemini function calling connects tools.", ["https://example.com/tools"])
    contradiction = Contradiction(
        cluster_id="contradiction_001",
        topic="workflow",
        side_a_claim=fact_a.claim,
        side_a_evidence_ids=["ev_001"],
        side_b_claim=fact_b.claim,
        side_b_evidence_ids=["ev_002"],
        resolution="unresolved",
    )
    ledger = FactLedger(verified_facts=[fact_a, fact_b], contradictions=[contradiction])
    report = make_report([fact_a])
    patch = CoveragePatch(
        coverage_score=0.8,
        patch_operations=[
            PatchOperation(
                op="add_caveat",
                target_section_id="sec_uncertainties",
                text="Resolve workflow uncertainty.",
                contradiction_ids=["contradiction_001"],
                reason="Contradiction omitted.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    section = result.report_v2.sections[-1]
    assert section.section_id == "sec_uncertainties"
    assert section.used_fact_ids == ["fact_001", "fact_002"]
    assert section.citations == ["https://example.com/grounding", "https://example.com/tools"]


def test_remove_unsupported_operation_accepts_a_known_result_id():
    report = make_report([make_fact("fact_001", "MI300X has 192GB memory.")])
    report.answer_summary = "Unsupported claim."
    report.sections[0].content = "Supported detail. Unsupported claim."
    ledger = FactLedger(
        verified_facts=[make_fact("fact_001", "MI300X has 192GB memory.")],
        unsupported_claims=[
            {
                "claim": "Unsupported claim.",
                "evidence_id": "ev_unsupported_001",
                "result_id": "result_unsupported_001",
            }
        ],
    )
    patch = CoveragePatch(
        coverage_score=0.8,
        patch_operations=[
            PatchOperation(
                op="remove_unsupported",
                text="Remove unsupported claim: Unsupported claim.",
                result_ids=["result_unsupported_001"],
                reason="Unsupported claim appears in report.",
            )
        ],
    )

    result = apply_patch(report, patch, ledger)

    assert "Unsupported claim." not in result.report_v2.answer_summary
    assert "Unsupported claim." not in result.report_v2.sections[0].content


def make_report(facts, content=None):
    return ResearchReport(
        report_id="report_v1",
        title="Compare GPUs",
        answer_summary="Initial report.",
        sections=[
            {
                "section_id": "sec_verified",
                "heading": "Verified",
                "content": content or "\n".join(fact.claim for fact in facts),
                "used_fact_ids": [fact.fact_id for fact in facts],
                "citations": sorted({url for fact in facts for url in fact.source_urls}),
            }
        ],
        key_findings=[
            {
                "finding": facts[0].claim,
                "fact_ids": [facts[0].fact_id],
                "citations": facts[0].source_urls,
                "confidence": facts[0].confidence,
            }
        ],
        confidence_score=0.5,
        confidence_breakdown={"coverage": 0.4, "verified_ratio": 0.5},
        used_fact_ids=[fact.fact_id for fact in facts],
        sources=sorted({url for fact in facts for url in fact.source_urls}),
    )


def make_fact(fact_id, claim, urls=None, status="VERIFIED"):
    return VerifiedFact(
        fact_id=fact_id,
        claim=claim,
        status=status,
        confidence=0.9 if status == "VERIFIED" else 0.55,
        supporting_evidence_ids=[fact_id.replace("fact", "ev")],
        source_urls=urls or ["https://example.com/source"],
    )
