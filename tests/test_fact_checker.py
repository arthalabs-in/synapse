import asyncio

from agents.fact_checker import FactCheckerAgent
from backend.models import EvidenceItem, JobEvidenceOutput, JobSearchOutput, PlannerOutput, ResearchJob, SearchCoverage, SearchHeader


def test_direct_support_becomes_verified():
    evidence = make_evidence(
        "ev_001",
        claim="AMD MI300X includes 192GB of HBM3 memory.",
        quote="AMD MI300X includes 192GB of HBM3 memory.",
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert len(ledger.verified_facts) == 1
    assert ledger.verified_facts[0].status == "VERIFIED"
    assert ledger.verified_facts[0].supporting_evidence_ids == ["ev_001"]


def test_weak_support_becomes_partial():
    evidence = make_evidence(
        "ev_001",
        claim="AMD MI300X is the fastest GPU for all inference workloads.",
        quote="AMD MI300X is designed for inference workloads.",
        limitations=["snippet-only evidence"],
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert len(ledger.partial_facts) == 1
    assert ledger.partial_facts[0].status == "PARTIAL"
    assert "caveat" in ledger.partial_facts[0].notes.lower()


def test_deterministic_fallback_evidence_defaults_to_partial():
    evidence = make_evidence(
        "ev_001",
        claim="Gemini agents use tools to complete multi-step tasks.",
        quote="Gemini agents use tools to complete multi-step tasks.",
        extraction_method="deterministic_fallback",
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert ledger.verified_facts == []
    assert len(ledger.partial_facts) == 1
    assert "deterministic fallback" in ledger.partial_facts[0].notes.lower()


def test_noisy_evidence_is_not_verified():
    evidence = make_evidence(
        "ev_001",
        claim="REST curl uses x-goog-api-key for Gemini.",
        quote='REST curl "https://generativelanguage.googleapis.com" -H "x-goog-api-key: $GEMINI_API_KEY"',
        limitations=["boilerplate_or_code"],
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert ledger.verified_facts == []
    assert ledger.partial_facts == []
    assert ledger.unsupported_claims[0]["reason"] == "evidence failed quality gate"


def test_evidence_marked_unrelated_by_extractor_is_unsupported():
    evidence = make_evidence(
        "ev_001",
        claim="This is a brief tutorial on least square estimation.",
        quote="This is a brief tutorial on the least square estimation technique.",
        limitations=["Source is unrelated to Gemini API or agents."],
        extraction_method="llm_batch",
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert ledger.verified_facts == []
    assert ledger.partial_facts == []
    assert ledger.unsupported_claims[0]["reason"] == "evidence failed quality gate"


def test_evidence_marked_not_general_or_not_gemini_specific_is_unsupported():
    evidence_items = [
        make_evidence(
            "ev_001",
            claim="Gemini Robotics controls robots.",
            quote="Gemini Robotics controls robots.",
            limitations=["This is specific to robotics domain, not general agent workflows."],
            extraction_method="llm_batch",
        ),
        make_evidence(
            "ev_002",
            claim="The paper discusses sandboxing.",
            quote="The paper discusses sandboxing.",
            limitations=["Does not mention Gemini-specific features or best practices for evidence grounding."],
            extraction_method="llm_batch",
        ),
    ]

    ledger = asyncio.run(make_checker(evidence_items))

    assert ledger.verified_facts == []
    assert ledger.partial_facts == []
    assert len(ledger.unsupported_claims) == 2


def test_no_support_becomes_unsupported():
    evidence = make_evidence(
        "ev_001",
        claim="AMD MI300X includes 192GB of HBM3 memory.",
        quote="NVIDIA H100 includes 80GB of HBM3 memory.",
    )

    ledger = asyncio.run(make_checker([evidence]))

    assert ledger.verified_facts == []
    assert len(ledger.unsupported_claims) == 1
    assert ledger.unsupported_claims[0]["claim"] == "AMD MI300X includes 192GB of HBM3 memory."


def test_evidence_that_does_not_support_claim_is_not_verified():
    evidence = make_evidence(
        "ev_001",
        claim="The paper proves that small models outperform large models on every benchmark.",
        quote="The paper reports that larger models outperformed smaller models on most benchmarks.",
    )

    ledger = asyncio.run(make_checker([evidence]))

    verified_claims = {fact.claim for fact in ledger.verified_facts}
    assert evidence.claim not in verified_claims


def test_conflicting_evidence_creates_contradiction():
    evidence_items = [
        make_evidence(
            "ev_001",
            claim="AMD MI300X has 192GB memory.",
            quote="AMD MI300X has 192GB memory.",
            url="https://example.com/a",
        ),
        make_evidence(
            "ev_002",
            claim="AMD MI300X has 128GB memory.",
            quote="AMD MI300X has 128GB memory.",
            url="https://example.com/b",
        ),
    ]

    ledger = asyncio.run(make_checker(evidence_items))

    assert len(ledger.contradictions) == 1
    assert set(ledger.contradictions[0].side_a_evidence_ids + ledger.contradictions[0].side_b_evidence_ids) == {
        "ev_001",
        "ev_002",
    }


def test_noisy_evidence_does_not_create_contradiction():
    evidence_items = [
        make_evidence(
            "ev_001",
            claim="Gemini Flash supports 100 requests.",
            quote="Gemini Flash supports 100 requests.",
            limitations=["boilerplate_or_code"],
        ),
        make_evidence(
            "ev_002",
            claim="Gemini Flash supports 200 requests.",
            quote="Gemini Flash supports 200 requests.",
        ),
    ]

    ledger = asyncio.run(make_checker(evidence_items))

    assert ledger.contradictions == []


def test_fact_checker_deduplicates_evidence_passed_both_flat_and_by_job():
    evidence = make_evidence(
        "ev_001",
        claim="The source says Gemini can be used to build AI agents.",
        quote="The source says Gemini can be used to build AI agents.",
    )
    header = SearchHeader(
        result_id=evidence.result_id,
        job_id=evidence.job_id,
        query="gemini agents",
        title=evidence.source_title,
        url=evidence.source_url,
        snippet="Search snippet is not fact.",
        rank=1,
        source_type_guess=evidence.source_type,
    )
    job_output = (
        JobSearchOutput(job_id=evidence.job_id, search_headers=[header], search_coverage=SearchCoverage(queries_run=1, results_found=1)),
        JobEvidenceOutput(job_id=evidence.job_id, evidence_items=[evidence]),
    )

    ledger = asyncio.run(
        FactCheckerAgent().check(
            original_query="What Gemini agent workflow should we build?",
            planner_output=make_planner(),
            research_job_outputs=[job_output],
            search_headers=[header],
            evidence_items=[evidence],
        )
    )

    assert len(ledger.verified_facts) == 1
    assert ledger.verified_facts[0].supporting_evidence_ids == ["ev_001"]


async def make_checker(evidence_items):
    job = ResearchJob(
        job_id="job_001",
        job_name="Fact check job",
        objective="Check facts.",
        search_queries=["mi300x memory"],
        source_priorities=["official"],
        must_answer=["memory"],
    )
    planner = PlannerOutput(
        original_query="What is MI300X memory?",
        query_interpretation="Find MI300X memory facts.",
        precontext_claims=[
            {
                "claim": "A source mentions MI300X memory.",
                "source_id": "src_001",
                "url": "https://example.com/source",
            }
        ],
        research_jobs=[job, job.model_copy(update={"job_id": "job_002"})],
    )
    headers = [
        SearchHeader(
            result_id=item.result_id,
            job_id=item.job_id,
            query="mi300x memory",
            title=item.source_title,
            url=item.source_url,
            snippet="Search snippet is not fact.",
            rank=index + 1,
            source_type_guess=item.source_type,
        )
        for index, item in enumerate(evidence_items)
    ]
    return await FactCheckerAgent().check(
        original_query="What is MI300X memory?",
        planner_output=planner,
        research_job_outputs=[],
        search_headers=headers,
        evidence_items=evidence_items,
    )


def make_planner():
    job = ResearchJob(
        job_id="job_001",
        job_name="Fact check job",
        objective="Check facts.",
        search_queries=["gemini agents"],
        source_priorities=["official"],
        must_answer=["agents"],
    )
    return PlannerOutput(
        original_query="What Gemini agent workflow should we build?",
        query_interpretation="Find Gemini agent workflow facts.",
        precontext_claims=[
            {
                "claim": "A source mentions Gemini agents.",
                "source_id": "src_001",
                "url": "https://example.com/source",
            }
        ],
        research_jobs=[job, job.model_copy(update={"job_id": "job_002"})],
    )


def make_evidence(
    evidence_id,
    claim,
    quote,
    url="https://example.com/source",
    limitations=None,
    extraction_method="deterministic",
):
    return EvidenceItem(
        evidence_id=evidence_id,
        job_id="job_001",
        result_id=f"res_{evidence_id}",
        claim=claim,
        source_title="Source",
        source_url=url,
        source_quote=quote,
        source_type="official",
        relevance_to_query=0.9,
        limitations=limitations or [],
        extraction_method=extraction_method,
    )




class _EmptyThenEmptyLLM:
    """LLM provider stub that always raises EmptyVisibleContentError."""

    def __init__(self):
        self.call_count = 0

    async def chat_json(self, messages, schema, **kwargs):  # pragma: no cover - exercised in test
        from backend.providers.llm.openai_compatible import EmptyVisibleContentError

        self.call_count += 1
        raise EmptyVisibleContentError(
            finish_reason="MAX_TOKENS",
            reasoning_tokens=2000,
            completion_tokens=0,
            max_tokens=kwargs.get("max_tokens", 3000),
        )


class _EmptyThenSuccessLLM:
    """First call raises EmptyVisibleContentError; second returns valid judgments."""

    def __init__(self):
        self.call_count = 0
        self.calls: list[dict] = []

    async def chat_json(self, messages, schema, **kwargs):
        from backend.providers.llm.openai_compatible import EmptyVisibleContentError
        from backend.models import LLMResponse

        self.call_count += 1
        self.calls.append(kwargs)
        if self.call_count == 1:
            raise EmptyVisibleContentError(
                finish_reason="MAX_TOKENS",
                reasoning_tokens=2000,
                completion_tokens=0,
                max_tokens=kwargs.get("max_tokens", 3000),
            )
        return LLMResponse(
            text='{"judgments":[]}',
            parsed_json={
                "judgments": [
                    {
                        "evidence_id": "ev_001",
                        "status": "VERIFIED",
                        "confidence": 0.9,
                        "explanation": "retry succeeded",
                        "quote_supports_claim": True,
                    }
                ]
            },
            model="gemini-2.5-pro",
            provider="gemini",
        )


def test_fact_checker_retries_once_on_empty_llm_response(monkeypatch):
    from agents.fact_checker import FactCheckerAgent

    monkeypatch.setattr("agents.fact_checker.config.FACT_CHECKER_LLM_RETRY_ON_EMPTY", True)

    llm = _EmptyThenSuccessLLM()
    agent = FactCheckerAgent(llm_provider=llm)
    evidence = make_evidence(
        "ev_001",
        claim="Gemini agents use tools to complete multi-step tasks.",
        quote="Gemini agents use tools to complete multi-step tasks.",
    )

    ledger = asyncio.run(
        agent.check(
            original_query="test",
            planner_output=make_planner(),
            research_job_outputs=[],
            search_headers=[],
            evidence_items=[evidence],
        )
    )

    assert llm.call_count == 2, "retry should fire exactly once"
    # Second call must raise max_tokens (6000 in the new path).
    assert llm.calls[1]["max_tokens"] == 6000
    assert any(fact.verification_method == "llm_batch" for fact in ledger.verified_facts)


def test_fact_checker_no_retry_when_flag_disabled(monkeypatch):
    from agents.fact_checker import FactCheckerAgent

    monkeypatch.setattr("agents.fact_checker.config.FACT_CHECKER_LLM_RETRY_ON_EMPTY", False)

    llm = _EmptyThenEmptyLLM()
    agent = FactCheckerAgent(llm_provider=llm)
    evidence = make_evidence(
        "ev_001",
        claim="Gemini agents use tools to complete multi-step tasks.",
        quote="Gemini agents use tools to complete multi-step tasks.",
    )

    ledger = asyncio.run(
        agent.check(
            original_query="test",
            planner_output=make_planner(),
            research_job_outputs=[],
            search_headers=[],
            evidence_items=[evidence],
        )
    )

    assert llm.call_count == 1, "retry must be skipped when flag is off"
    # Heuristic fallback still classifies the evidence.
    assert len(ledger.verified_facts) + len(ledger.partial_facts) >= 1
