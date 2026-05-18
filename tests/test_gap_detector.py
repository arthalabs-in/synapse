import asyncio

import pytest
from pydantic import ValidationError

from agents.gap_detector import CoverageAuditorAgent
from backend.models import (
    Contradiction,
    CoveragePatch,
    EvidenceItem,
    FactLedger,
    PatchOperation,
    PlannerOutput,
    ResearchJob,
    ResearchReport,
    SearchHeader,
    VerifiedFact,
)


def test_detects_unused_verified_fact():
    fact_used = make_fact("fact_001", "MI300X has 192GB memory.", ["https://example.com/a"])
    fact_unused = make_fact("fact_002", "H100 has 80GB memory.", ["https://example.com/b"])
    report = make_report([fact_used])
    patch = asyncio.run(make_auditor().audit("Compare GPUs", make_planner(), [], [], make_ledger([fact_used, fact_unused]), report))

    assert patch.missed_verified_details == [{"fact_id": "fact_002", "claim": "H100 has 80GB memory."}]
    assert any(op.fact_ids == ["fact_002"] and op.op == "add" for op in patch.patch_operations)


def test_detects_missing_contradiction():
    fact = make_fact("fact_001", "MI300X has 192GB memory.", ["https://example.com/a"])
    contradiction = Contradiction(
        cluster_id="contradiction_001",
        topic="memory",
        side_a_claim="MI300X has 192GB memory.",
        side_a_evidence_ids=["ev_001"],
        side_b_claim="MI300X has 128GB memory.",
        side_b_evidence_ids=["ev_002"],
        resolution="unresolved",
    )
    ledger = make_ledger([fact], contradictions=[contradiction])
    report = make_report([fact], contradictions=[])

    patch = asyncio.run(make_auditor().audit("Compare GPUs", make_planner(), [], [], ledger, report))

    assert patch.missed_contradictions[0]["contradiction_id"] == "contradiction_001"
    assert any(op.contradiction_ids == ["contradiction_001"] for op in patch.patch_operations)


def test_refuses_patch_with_no_fact_id():
    with pytest.raises(ValidationError, match="must reference"):
        CoveragePatch(
            coverage_score=0.5,
            patch_operations=[
                PatchOperation(
                    op="add",
                    target_section_id="sec_verified",
                    text="Unsupported patch.",
                    reason="No reference.",
                )
            ],
        )


def test_does_not_rewrite_whole_report():
    facts = [
        make_fact("fact_001", "MI300X has 192GB memory.", ["https://example.com/a"]),
        make_fact("fact_002", "H100 has 80GB memory.", ["https://example.com/b"]),
    ]
    report = make_report([facts[0]])

    patch = asyncio.run(make_auditor().audit("Compare GPUs", make_planner(), [], [], make_ledger(facts), report))

    assert patch.patch_operations
    assert all(op.op != "replace" for op in patch.patch_operations)
    assert all(len(op.text) < len(report.answer_summary) + sum(len(section.content) for section in report.sections) for op in patch.patch_operations)


def test_does_not_patch_noisy_boilerplate_facts_into_report():
    fact_used = make_fact("fact_001", "Gemini supports grounded agent workflows.", ["https://example.com/a"])
    noisy = make_fact(
        "fact_002",
        "text ); } REST curl \"https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent\" -H \"x-goog-api-key: $GEMINI_API_KEY\" -X POST",
        ["https://example.com/b"],
    )
    report = make_report([fact_used])

    patch = asyncio.run(make_auditor().audit("Gemini demo", make_planner(), [], [], make_ledger([fact_used, noisy]), report))

    assert patch.missed_verified_details == [{"fact_id": "fact_002", "claim": noisy.claim}]
    assert not patch.patch_operations


def test_llm_authored_report_records_missed_facts_without_deterministic_append_patch():
    fact_used = make_fact("fact_001", "Gemini supports grounded agent workflows.", ["https://example.com/a"])
    fact_unused = make_fact("fact_002", "Gemini supports function calling.", ["https://example.com/b"])
    report = make_report([fact_used])
    report.sections[0].section_id = "sec_llm_01"

    patch = asyncio.run(make_auditor().audit("Gemini demo", make_planner(), [], [], make_ledger([fact_used, fact_unused]), report))

    assert patch.missed_verified_details == [{"fact_id": "fact_002", "claim": fact_unused.claim}]
    assert patch.patch_operations == []


def test_llm_diff_agent_receives_full_pipeline_context_and_skill():
    fact_used = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    fact_unused = make_fact("fact_002", "LangGraph provides visibility and control.", ["https://example.com/langgraph"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": [{"intent": "option balance", "reason": "LangGraph section is missing"}],
            "unused_supported_facts": [{"fact_id": "fact_002", "reason": "Relevant LangGraph evidence unused"}],
            "option_balance_gaps": [{"option": "LangGraph", "fact_ids": ["fact_002"]}],
            "missed_contradictions_or_caveats": [],
            "unsupported_slips": [],
            "suggested_revision_focus": ["Revise LangGraph using fact_002."],
        }
    )
    report = make_report([fact_used])
    report.sections[0].section_id = "sec_llm_01"
    fetched_summary = {"fetched_http_count": 2, "failed_count": 0}
    provider_metrics = {"run_quality": {"score": 0.71}, "llm_call_count": 3}

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare ADK vs LangGraph",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact_used, fact_unused]),
            report,
            fetched_source_summary=fetched_summary,
            provider_metrics=provider_metrics,
            run_quality=provider_metrics["run_quality"],
        )
    )

    prompt = provider.messages_seen[0][1]["content"]
    assert provider.kwargs_seen[0]["skills"]
    assert provider.kwargs_seen[0]["reasoning_effort"] == "high"
    assert "coverage-diff" in provider.kwargs_seen[0]["skills"][0]
    assert "Compare ADK vs LangGraph" in prompt
    assert "coverage_checklist" in prompt
    assert "research_jobs" in prompt
    assert "search_headers" in prompt
    assert "fetched_source_summary" in prompt
    assert "evidence_items" in prompt
    assert "verified_facts" in prompt
    assert "partial_facts" in prompt
    assert "contradictions" in prompt
    assert "unsupported_claims" in prompt
    assert "report_v1" in prompt
    assert "provider_metrics" in prompt
    assert "run_quality" in prompt
    assert patch.revision_brief["option_balance_gaps"][0]["option"] == "LangGraph"
    assert patch.coverage_diff.revision_brief["suggested_revision_focus"] == ["Revise LangGraph using fact_002."]


def test_llm_diff_agent_accepts_string_lists_from_model():
    fact = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": ["latency/cost"],
            "unused_supported_facts": ["fact_001"],
            "option_balance_gaps": ["custom async Python has no direct evidence"],
            "missed_contradictions_or_caveats": ["partial support caveat needed"],
            "unsupported_slips": [],
            "suggested_revision_focus": ["Weaken unsupported claims."],
        }
    )
    report = make_report([fact])
    report.sections[0].section_id = "sec_llm_01"
    report.sections[0].content = "ADK guarantees deterministic tool execution."

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare architectures",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact]),
            report,
        )
    )

    assert patch.revision_brief["missing_intent"] == ["latency/cost"]
    assert patch.revision_brief["suggested_revision_focus"] == ["Weaken unsupported claims."]


def test_llm_diff_agent_returns_ui_ready_grounded_patch_operations():
    fact = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": [],
            "unused_supported_facts": [],
            "option_balance_gaps": [],
            "missed_contradictions_or_caveats": [],
            "unsupported_slips": [],
            "suggested_revision_focus": ["Weaken ADK wording."],
            "patch_operations": [
                {
                    "edit_id": "edit_001",
                    "op": "weaken",
                    "target_section_id": "sec_llm_01",
                    "target_path": "sections[section_id=sec_llm_01].content",
                    "edit_label": "Weaken ADK certainty",
                    "original_text": "ADK guarantees deterministic tool execution.",
                    "replacement_text": "ADK supports predictable tool pipelines.",
                    "text": "ADK supports predictable tool pipelines.",
                    "fact_ids": ["fact_001"],
                    "reason": "The stronger wording is not supported by the cited fact.",
                }
            ],
        }
    )
    report = make_report([fact])
    report.sections[0].section_id = "sec_llm_01"
    report.sections[0].content = "ADK guarantees deterministic tool execution."

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare architectures",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact]),
            report,
        )
    )

    assert len(patch.patch_operations) == 1
    operation = patch.patch_operations[0]
    assert operation.edit_id == "edit_001"
    assert operation.target_path == "sections[section_id=sec_llm_01].content"
    assert operation.edit_label == "Weaken ADK certainty"
    assert operation.original_text == "ADK guarantees deterministic tool execution."
    assert operation.replacement_text == "ADK supports predictable tool pipelines."
    assert operation.reason == "The stronger wording is not supported by the cited fact."


def test_llm_diff_agent_uses_replacement_text_when_patch_text_is_empty():
    fact = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": [],
            "unused_supported_facts": [],
            "option_balance_gaps": [],
            "missed_contradictions_or_caveats": [],
            "unsupported_slips": [],
            "suggested_revision_focus": ["Weaken ADK wording."],
            "patch_operations": [
                {
                    "edit_id": "edit_001",
                    "op": "weaken",
                    "target_section_id": "sec_llm_01",
                    "target_path": "sections[section_id=sec_llm_01].content",
                    "original_text": "ADK guarantees deterministic tool execution.",
                    "replacement_text": "ADK supports predictable tool pipelines.",
                    "fact_ids": ["fact_001"],
                    "reason": "Use the replacement text as the applied patch body.",
                }
            ],
        }
    )
    report = make_report([fact])
    report.sections[0].section_id = "sec_llm_01"
    report.sections[0].content = "ADK guarantees deterministic tool execution."

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare architectures",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact]),
            report,
        )
    )

    assert patch.patch_operations[0].text == "ADK supports predictable tool pipelines."


def test_llm_diff_agent_drops_unsafe_patch_operations_but_keeps_revision_brief():
    fact = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": [],
            "unused_supported_facts": [],
            "option_balance_gaps": [],
            "missed_contradictions_or_caveats": [],
            "unsupported_slips": ["Unsupported custom async claim."],
            "suggested_revision_focus": ["Remove unsupported custom async claim."],
            "patch_operations": [
                {
                    "edit_id": "edit_bad",
                    "op": "weaken",
                    "target_section_id": "sec_llm_01",
                    "target_path": "sections[section_id=sec_llm_01].content",
                    "original_text": "Custom async Python has no observability.",
                    "replacement_text": "Custom async Python has no observability.",
                    "text": "Custom async Python has no observability.",
                    "fact_ids": ["fact_missing"],
                    "reason": "Unknown fact IDs must not be applied.",
                }
            ],
        }
    )
    report = make_report([fact])
    report.sections[0].section_id = "sec_llm_01"

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare architectures",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact]),
            report,
        )
    )

    assert patch.patch_operations == []
    assert patch.revision_brief["patch_operations"][0]["edit_id"] == "edit_bad"


def test_llm_diff_agent_keeps_patch_when_original_text_is_not_at_location():
    fact = make_fact("fact_001", "ADK supports predictable tool pipelines.", ["https://example.com/adk"])
    provider = FakeDiffLLMProvider(
        {
            "missing_intent": [],
            "unused_supported_facts": [],
            "option_balance_gaps": [],
            "missed_contradictions_or_caveats": [],
            "unsupported_slips": [],
            "suggested_revision_focus": ["Weaken ADK wording."],
            "patch_operations": [
                {
                    "edit_id": "edit_missing_span",
                    "op": "weaken",
                    "target_section_id": "sec_llm_01",
                    "target_path": "sections[section_id=sec_llm_01].content",
                    "original_text": "This exact span is not in the report.",
                    "replacement_text": "ADK supports predictable tool pipelines.",
                    "text": "ADK supports predictable tool pipelines.",
                    "fact_ids": ["fact_001"],
                    "reason": "Avoid applying a diff that cannot be located.",
                }
            ],
        }
    )
    report = make_report([fact])
    report.sections[0].section_id = "sec_llm_01"

    patch = asyncio.run(
        CoverageAuditorAgent(llm_provider=provider).audit(
            "Compare architectures",
            make_planner(),
            [make_header("res_001")],
            [make_evidence("ev_001", "res_001")],
            make_ledger([fact]),
            report,
        )
    )

    assert patch.patch_operations[0].edit_id == "edit_missing_span"
    assert patch.patch_operations[0].text == "ADK supports predictable tool pipelines."


def make_auditor():
    return CoverageAuditorAgent()


def make_planner():
    job = ResearchJob(
        job_id="job_001",
        job_name="GPU facts",
        objective="Find GPU facts.",
        search_queries=["gpu memory"],
        source_priorities=["official"],
        must_answer=["memory"],
    )
    return PlannerOutput(
        original_query="Compare GPUs",
        query_interpretation="Compare GPU memory.",
        precontext_claims=[
            {"claim": "GPU memory is relevant.", "source_id": "src_001", "url": "https://example.com/a"}
        ],
        research_jobs=[job, job.model_copy(update={"job_id": "job_002"})],
        coverage_checklist=["memory"],
    )


def make_ledger(facts, partial=None, contradictions=None, unsupported=None):
    return FactLedger(
        verified_facts=facts,
        partial_facts=partial or [],
        contradictions=contradictions or [],
        unsupported_claims=unsupported or [],
        source_quality_summary={"official": len(facts)},
    )


def make_report(facts, contradictions=None):
    return ResearchReport(
        title="Compare GPUs",
        answer_summary=" ".join(fact.claim for fact in facts),
        sections=[
            {
                "section_id": "sec_verified",
                "heading": "Verified",
                "content": "\n".join(fact.claim for fact in facts),
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
        contradictions_or_uncertainties=contradictions or [],
        confidence_score=0.7,
        confidence_breakdown={"verified_ratio": 1.0},
        used_fact_ids=[fact.fact_id for fact in facts],
        sources=sorted({url for fact in facts for url in fact.source_urls}),
    )


def make_header(result_id):
    return SearchHeader(
        result_id=result_id,
        job_id="job_001",
        query="agent architecture",
        title="Architecture source",
        url="https://example.com/source",
        snippet="Useful source.",
        rank=1,
        source_type_guess="official",
    )


def make_evidence(evidence_id, result_id):
    return EvidenceItem(
        evidence_id=evidence_id,
        job_id="job_001",
        result_id=result_id,
        claim="ADK supports predictable tool pipelines.",
        source_title="Architecture source",
        source_url="https://example.com/source",
        source_quote="ADK supports predictable tool pipelines.",
        quote_location="page",
        source_type="official",
        source_quality_score=0.9,
        extraction_method="llm_batch",
        relevance_to_query=0.8,
    )


def make_fact(fact_id, claim, urls, status="VERIFIED"):
    return VerifiedFact(
        fact_id=fact_id,
        claim=claim,
        status=status,
        confidence=0.9 if status == "VERIFIED" else 0.55,
        supporting_evidence_ids=[fact_id.replace("fact", "ev")],
        source_urls=urls,
    )


class FakeDiffLLMProvider:
    def __init__(self, payload):
        self.payload = payload
        self.messages_seen = []
        self.kwargs_seen = []

    async def chat_json(self, messages, schema, temperature, max_tokens, **kwargs):
        self.messages_seen.append(messages)
        self.kwargs_seen.append(kwargs)
        schema.model_validate(self.payload)
        return type("Response", (), {"parsed_json": self.payload})()
