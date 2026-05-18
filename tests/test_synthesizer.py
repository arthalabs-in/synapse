import asyncio

import pytest
from pydantic import ValidationError

from agents.synthesizer import SynthesisDegradedError, SynthesizerAgent
from backend.models import FactLedger, LLMResponse, PlannerOutput, ResearchJob, ResearchReport, VerifiedFact


def test_synthesizer_excludes_unsupported_claims():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "AMD MI300X includes 192GB of HBM3 memory.",
                ["https://example.com/mi300x"],
            )
        ],
        unsupported=[
            {
                "claim": "AMD MI300X is fastest for every workload.",
                "evidence_id": "ev_bad",
                "reason": "source quote does not support claim",
            }
        ],
    )

    report = asyncio.run(make_synthesizer().synthesize("Compare GPUs", make_planner(), [], ledger))

    assert "192GB" in report.answer_summary
    assert "fastest for every workload" not in report.answer_summary
    assert all("fastest for every workload" not in section.content for section in report.sections)
    assert report.unsupported_not_included == ledger.unsupported_claims


def test_every_section_has_fact_ids_and_key_findings_have_citations():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "AMD MI300X includes 192GB of HBM3 memory.",
                ["https://example.com/mi300x"],
            )
        ],
        partial=[
            make_fact(
                "fact_002",
                "Benchmark results vary by workload.",
                ["https://example.com/benchmarks"],
                status="PARTIAL",
                notes="Partial support; caveat required",
            )
        ],
    )

    report = asyncio.run(make_synthesizer().synthesize("Compare GPUs", make_planner(), [], ledger))

    assert report.sections
    assert all(section.used_fact_ids for section in report.sections)
    assert all(section.citations for section in report.sections)
    assert all(finding.fact_ids for finding in report.key_findings)
    assert all(finding.citations for finding in report.key_findings)
    assert "Caveat" in report.sections[-1].content


def test_confidence_score_is_between_zero_and_one():
    report = asyncio.run(
        make_synthesizer().synthesize(
            "Compare GPUs",
            make_planner(),
            [{"job_id": "job_001", "results_found": 3}],
            make_ledger(
                verified=[
                    make_fact(
                        "fact_001",
                        "AMD MI300X includes 192GB of HBM3 memory.",
                        ["https://example.com/mi300x"],
                    )
                ]
            ),
        )
    )

    assert 0 <= report.confidence_score <= 1
    assert set(report.confidence_breakdown) == {
        "verified_ratio",
        "source_quality",
        "agreement",
        "recency",
        "coverage",
    }


def test_synthesizer_uses_llm_provider_for_report_copy():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "Gemini supports function calling for structured agent actions.",
                ["https://ai.google.dev/gemini-api/docs/function-calling"],
            )
        ]
    )
    provider = FakeReportLLMProvider(
        "TITLE: Gemini agent workflow recommendation\n"
        "SUMMARY: Build the demo around a Gemini agent that plans, calls tools, and audits its own evidence.\n"
        "SECTION: Recommended Build\n"
        "A Gemini-led agent loop is the sharpest fit because the cited fact supports tool-backed agent actions."
    )

    report = asyncio.run(SynthesizerAgent(llm_provider=provider).synthesize("Pick a Gemini hackathon build", make_planner(), [], ledger))

    assert provider.calls == 1
    assert report.title == "Gemini agent workflow recommendation"
    assert report.answer_summary.startswith("Build the demo around a Gemini agent")
    assert report.sections[0].heading == "Recommended Build"
    assert report.sections[0].used_fact_ids == ["fact_001"]
    assert report.sections[0].citations == ["https://ai.google.dev/gemini-api/docs/function-calling"]
    assert report.key_findings[0].citations == ["https://ai.google.dev/gemini-api/docs/function-calling"]


def test_synthesizer_does_not_silently_fall_back_when_llm_fails():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "AMD MI300X includes 192GB of HBM3 memory.",
                ["https://example.com/mi300x"],
            )
        ]
    )

    with pytest.raises(SynthesisDegradedError):
        asyncio.run(SynthesizerAgent(llm_provider=FailingReportLLMProvider()).synthesize(
            "Compare GPUs",
            make_planner(),
            [],
            ledger,
        ))


def test_synthesizer_attributes_inline_fact_ids_per_section():
    ledger = make_ledger(
        verified=[
            make_fact("fact_001", "Gemini supports function calling.", ["https://example.com/function-calling"]),
            make_fact("fact_002", "Gemini supports grounding.", ["https://example.com/grounding"]),
        ]
    )
    provider = FakeReportLLMProvider(
        "TITLE: Gemini workflow\n"
        "SUMMARY: Build around tools [fact_001] and grounding [fact_002].\n"
        "SECTION: Tool Loop\n"
        "Use function calling for actions. [fact_001]\n"
        "SECTION: Grounding\n"
        "Use grounding for current evidence. [fact_002]"
    )

    report = asyncio.run(SynthesizerAgent(llm_provider=provider).synthesize("Pick build", make_planner(), [], ledger))

    assert report.sections[0].used_fact_ids == ["fact_001"]
    assert report.sections[0].citations == ["https://example.com/function-calling"]
    assert report.sections[1].used_fact_ids == ["fact_002"]
    assert report.sections[1].citations == ["https://example.com/grounding"]


def test_synthesizer_passes_research_synthesis_skill_to_llm_provider():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "Gemini supports function calling for structured agent actions.",
                ["https://ai.google.dev/gemini-api/docs/function-calling"],
            )
        ]
    )
    provider = SequentialReportLLMProvider(
        [
            "TITLE: Skill-aware report\n"
            "SUMMARY: Use evidence before recommendation. [fact_001]\n"
            "SECTION: Recommendation\n"
            "Recommend the option only after weighing evidence. [fact_001]"
        ]
    )

    asyncio.run(SynthesizerAgent(llm_provider=provider).synthesize("Pick a Gemini hackathon build", make_planner(), [], ledger))

    skills = provider.kwargs_seen[0]["skills"]
    assert len(skills) == 1
    assert "Evidence-First" in skills[0]
    assert "do not treat absence of evidence as proof of absence" in skills[0]


def test_synthesizer_retries_empty_visible_llm_response():
    ledger = make_ledger(
        verified=[
            make_fact(
                "fact_001",
                "Gemini supports function calling for structured agent actions.",
                ["https://ai.google.dev/gemini-api/docs/function-calling"],
            )
        ]
    )
    provider = SequentialReportLLMProvider(
        [
            "",
            "TITLE: Retry worked\nSUMMARY: The live report should be visible.\nSECTION: Recommendation\nBuild the tool-calling Gemini agent.",
        ]
    )

    report = asyncio.run(SynthesizerAgent(llm_provider=provider).synthesize("Pick a Gemini hackathon build", make_planner(), [], ledger))

    assert provider.calls == 2
    assert report.title == "Retry worked"
    assert report.answer_summary == "The live report should be visible."
    assert provider.kwargs_seen[1]["reasoning_effort"] == "high"


def test_report_fails_validation_if_citations_are_missing():
    with pytest.raises(ValidationError, match="citations"):
        ResearchReport(
            title="Invalid",
            answer_summary="A claim without citation.",
            sections=[
                {
                    "section_id": "sec_001",
                    "heading": "Finding",
                    "content": "AMD MI300X includes 192GB memory.",
                    "used_fact_ids": ["fact_001"],
                    "citations": [],
                }
            ],
            key_findings=[],
            confidence_score=0.5,
            confidence_breakdown={"verified_ratio": 1.0},
            used_fact_ids=["fact_001"],
        )


def make_synthesizer():
    return SynthesizerAgent()


def make_planner():
    job = ResearchJob(
        job_id="job_001",
        job_name="GPU evidence",
        objective="Find GPU facts.",
        search_queries=["mi300x memory"],
        source_priorities=["official"],
        must_answer=["memory"],
    )
    return PlannerOutput(
        original_query="Compare GPUs",
        query_interpretation="Compare GPU evidence.",
        precontext_claims=[
            {
                "claim": "Source mentions MI300X memory.",
                "source_id": "src_001",
                "url": "https://example.com/mi300x",
            }
        ],
        research_jobs=[job, job.model_copy(update={"job_id": "job_002"})],
        coverage_checklist=["memory", "benchmarks"],
    )


def make_ledger(verified=None, partial=None, unsupported=None):
    return FactLedger(
        verified_facts=verified or [],
        partial_facts=partial or [],
        unsupported_claims=unsupported or [],
        source_quality_summary={"official": len(verified or []) + len(partial or [])},
    )


def make_fact(fact_id, claim, urls, status="VERIFIED", notes=""):
    return VerifiedFact(
        fact_id=fact_id,
        claim=claim,
        status=status,
        confidence=0.9 if status == "VERIFIED" else 0.55,
        supporting_evidence_ids=[fact_id.replace("fact", "ev")],
        source_urls=urls,
        notes=notes,
    )


class FakeReportLLMProvider:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    async def chat_text(self, messages, temperature, max_tokens, **kwargs):
        self.calls += 1
        return LLMResponse(
            text=self.text,
            parsed_json=None,
            model="fake",
            provider="fake",
        )

    async def chat_json(self, messages, schema, temperature, max_tokens):
        raise AssertionError("synthesis should use chat_text for resilient live report copy")


class FailingReportLLMProvider:
    async def chat_text(self, messages, temperature, max_tokens, **kwargs):
        raise TimeoutError("model timed out")


class SequentialReportLLMProvider:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0
        self.kwargs_seen = []

    async def chat_text(self, messages, temperature, max_tokens, **kwargs):
        self.kwargs_seen.append({"temperature": temperature, "max_tokens": max_tokens, **kwargs})
        text = self.texts[self.calls]
        self.calls += 1
        return LLMResponse(
            text=text,
            parsed_json=None,
            model="fake",
            provider="fake",
        )
