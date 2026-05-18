import asyncio

import pytest

from agents.planner import PlannerAgent, PlannerValidationError
from backend.models import PlannerOutput, ResearchJob, SearchHeader


def test_planner_runs_precontext_search_and_returns_two_jobs():
    search = FakeSearchClient()
    llm = FakeLLMClient([valid_planner_output()])
    agent = PlannerAgent(search_client=search, llm_client=llm)

    result = asyncio.run(agent.plan("Compare AMD MI300X and NVIDIA H100 inference"))

    assert isinstance(result, PlannerOutput)
    assert result.query_interpretation == "Compare inference tradeoffs."
    assert len(result.precontext_claims) == 2
    assert len(result.research_jobs) == 2
    assert result.coverage_checklist == ["memory", "throughput", "software"]
    assert len(search.web_queries) == 3
    assert len(search.arxiv_queries) == 1
    assert "Search precontext" in llm.messages_seen[0][0]["content"]
    assert "Do not answer the user" in llm.messages_seen[0][0]["content"]


def test_planner_skips_arxiv_for_nontechnical_query():
    search = FakeSearchClient()
    llm = FakeLLMClient([valid_planner_output()])
    agent = PlannerAgent(search_client=search, llm_client=llm)

    asyncio.run(agent.plan("Best ergonomic habits for studying"))

    assert len(search.web_queries) == 3
    assert search.arxiv_queries == []


def test_planner_retries_once_when_validation_fails():
    invalid = valid_planner_output(research_jobs=[valid_job("job_a")])
    llm = FakeLLMClient([invalid, valid_planner_output()])
    agent = PlannerAgent(search_client=FakeSearchClient(), llm_client=llm)

    result = asyncio.run(agent.plan("LLM inference benchmarks"))

    assert len(result.research_jobs) == 2
    assert len(llm.messages_seen) == 2
    assert "FAILED VALIDATION" in llm.messages_seen[1][-1]["content"]


def test_planner_rejects_invented_precontext_citation():
    output = valid_planner_output()
    output.precontext_claims[0].url = "https://invented.example.com/source"
    llm = FakeLLMClient([output, output])
    agent = PlannerAgent(search_client=FakeSearchClient(), llm_client=llm)

    with pytest.raises(PlannerValidationError, match="precontext"):
        asyncio.run(agent.plan("GPU inference benchmarks"))


def test_planner_raises_after_retry_failure():
    invalid = valid_planner_output(research_jobs=[valid_job("job_a")])
    llm = FakeLLMClient([invalid, invalid])
    agent = PlannerAgent(search_client=FakeSearchClient(), llm_client=llm)

    with pytest.raises(PlannerValidationError):
        asyncio.run(agent.plan("GPU inference benchmarks"))


def test_planner_falls_back_on_llm_rate_limit_with_query_specific_jobs():
    llm = FailingLLMClient(RuntimeError("429 Too Many Requests"))
    agent = PlannerAgent(search_client=FakeSearchClient(), llm_client=llm)

    result = asyncio.run(agent.plan("Which evidence-backed AI agent workflow should we build for the Milan AI Week Gemini track?"))

    assert len(result.research_jobs) == 2
    assert result.planning_risks
    joined_queries = " ".join(query for job in result.research_jobs for query in job.search_queries)
    assert "Milan AI Week Gemini track" in joined_queries
    assert "MI300X" not in joined_queries
    assert "H100" not in joined_queries


class FakeSearchClient:
    def __init__(self):
        self.web_queries = []
        self.arxiv_queries = []

    async def search_web(self, query, max_results):
        self.web_queries.append((query, max_results))
        return [
            SearchHeader(
                result_id=f"web_{len(self.web_queries)}_001",
                job_id="web",
                query=query,
                title=f"Web source {len(self.web_queries)}",
                url=f"https://example.com/web-{len(self.web_queries)}",
                snippet="A search snippet, not evidence.",
                rank=1,
                source_type_guess="official",
            )
        ]

    async def search_arxiv(self, query, max_results):
        self.arxiv_queries.append((query, max_results))
        return [
            SearchHeader(
                result_id=f"arxiv_{len(self.arxiv_queries)}_001",
                job_id="arxiv",
                query=query,
                title="Paper source",
                url="https://arxiv.org/abs/1234.5678",
                snippet="A paper abstract snippet.",
                rank=1,
                source_type_guess="paper",
            )
        ]


class FakeLLMClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.messages_seen = []

    async def chat_json(self, messages, schema, temperature, max_tokens, thinking_enabled=False):
        self.messages_seen.append(messages)
        return self.outputs.pop(0)


class FailingLLMClient:
    def __init__(self, error):
        self.error = error
        self.messages_seen = []

    async def chat_json(self, messages, schema, temperature, max_tokens, thinking_enabled=False):
        self.messages_seen.append(messages)
        raise self.error


def valid_planner_output(research_jobs=None):
    return PlannerOutput(
        original_query="Compare AMD MI300X and NVIDIA H100 inference",
        query_interpretation="Compare inference tradeoffs.",
        precontext_claims=[
            {
                "claim": "Source one discusses MI300X.",
                "source_id": "web_1_001",
                "url": "https://example.com/web-1",
                "support_level": "weak",
            },
            {
                "claim": "Source two discusses H100.",
                "source_id": "web_2_001",
                "url": "https://example.com/web-2",
                "support_level": "weak",
            },
        ],
        research_jobs=research_jobs or [valid_job("job_a"), valid_job("job_b")],
        coverage_checklist=["memory", "throughput", "software"],
        planner_confidence=0.8,
    )


def valid_job(job_id):
    return ResearchJob(
        job_id=job_id,
        job_name=f"{job_id} evidence",
        objective="Find independently verifiable sources.",
        search_queries=["MI300X H100 inference benchmark"],
        source_priorities=["official", "paper"],
        must_answer=["memory capacity", "throughput"],
    )
