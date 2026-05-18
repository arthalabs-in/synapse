from backend.models import FetchedSource, ResearchJob, SearchHeader
from backend.reranker import rank_fetched_sources, rank_search_headers, select_deep_review_context, select_source_context


def test_rank_search_headers_caps_and_prioritizes_relevant_sources():
    job = make_job()
    headers = [
        make_header("low", "Unrelated cooking blog", "https://blog.example/cooking", "Recipe notes", "blog", rank=1),
        make_header("official", "AMD MI300X inference memory", "https://amd.com/mi300x", "MI300X HBM3 memory for LLM inference", "official", rank=3),
        make_header("paper", "LLM inference benchmark H100 MI300X", "https://arxiv.org/abs/2401.00001", "benchmark throughput", "paper", rank=2),
    ]

    ranked = rank_search_headers("MI300X H100 LLM inference memory", [job], headers, limit=2)

    assert len(ranked) == 2
    assert ranked[0].result_id == "official"
    assert {header.result_id for header in ranked} == {"official", "paper"}


def test_rank_search_headers_preserves_at_least_one_header_per_job_when_possible():
    job_a = make_job("job_a")
    job_b = make_job("job_b")
    headers = [
        make_header(f"a_{index}", f"Gemini grounding official source {index}", f"https://example.com/a/{index}", "grounding function calling", "official", job_id="job_a")
        for index in range(6)
    ]
    headers.append(
        make_header(
            "b_1",
            "Multimodal hackathon demo feasibility",
            "https://example.com/b/1",
            "image video audio demo",
            "blog",
            job_id="job_b",
            rank=8,
        )
    )

    ranked = rank_search_headers("Gemini agent hackathon", [job_a, job_b], headers, limit=4)

    assert len(ranked) == 4
    assert any(header.job_id == "job_b" for header in ranked)


def test_rank_fetched_sources_caps_to_best_successful_sources():
    job = make_job()
    headers = [
        make_header("official", "AMD MI300X", "https://amd.com/mi300x", "memory inference", "official"),
        make_header("blog", "Random post", "https://blog.example/post", "memory inference", "blog"),
        make_header("failed", "Failed", "https://failed.example", "memory inference", "official"),
    ]
    sources = [
        make_source("official", "https://amd.com/mi300x", "AMD MI300X memory inference " * 100, "official", 0.9),
        make_source("blog", "https://blog.example/post", "Some inference notes " * 100, "blog", 0.3),
        make_source("failed", "https://failed.example", "", "official", 0.9, success=False),
    ]

    ranked = rank_fetched_sources("MI300X H100 LLM inference memory", [job], sources, headers, limit=1)

    assert len(ranked) == 1
    assert ranked[0].result_id == "official"


def test_rank_fetched_sources_skips_thin_shell_pages():
    job = make_job()
    headers = [
        make_header("thin", "Gemini demo video shell", "https://youtube.com/watch?v=1", "Gemini demo", "blog"),
        make_header("official", "Gemini agents overview", "https://ai.google.dev/gemini-api/docs/agents", "function calling grounding", "official"),
    ]
    sources = [
        make_source("thin", "https://youtube.com/watch?v=1", "Gemini hackathon demo title only.", "blog", 0.45),
        make_source("official", "https://ai.google.dev/gemini-api/docs/agents", "Function calling and grounding with Gemini agents. " * 20, "official", 0.95),
    ]

    ranked = rank_fetched_sources("Gemini function calling grounding", [job], sources, headers, limit=2)

    assert [source.result_id for source in ranked] == ["official"]


def test_context_selectors_respect_token_budgets():
    job = make_job()
    source = make_source("official", "https://amd.com/mi300x", "MI300X memory throughput. " * 2000, "official", 0.9)

    normal = select_source_context(source, job, token_budget=100)
    deep = select_deep_review_context(source, job, token_budget=500)

    assert len(normal) <= 400
    assert len(deep) <= 2000


def make_job(job_id="job_a"):
    return ResearchJob(
        job_id=job_id,
        job_name="Hardware",
        objective="Compare MI300X and H100 LLM inference memory and throughput.",
        search_queries=["MI300X H100 LLM inference"],
        source_priorities=["official", "paper"],
        must_answer=["memory", "throughput"],
    )


def make_header(result_id, title, url, snippet, source_type, rank=1, job_id="job_a"):
    return SearchHeader(
        result_id=result_id,
        job_id=job_id,
        query="MI300X H100 LLM inference",
        title=title,
        url=url,
        snippet=snippet,
        rank=rank,
        provider="duckduckgo",
        source_type_guess=source_type,
    )


def make_source(result_id, url, text, source_type, quality, success=True):
    return FetchedSource(
        source_id=f"src_{result_id}",
        result_id=result_id,
        url=url,
        title=result_id,
        text=text,
        source_type=source_type,
        source_quality_score=quality,
        provider="http",
        fetch_status="fetched_http" if success else "failed",
        success=success,
    )
