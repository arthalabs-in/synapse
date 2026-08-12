import asyncio

from agents.evidence_extractor import EvidenceExtractorAgent
from agents.searcher import SearcherAgent
from backend.models import FetchedSource, LLMResponse, ResearchJob, SearchHeader


def test_searcher_runs_job_queries_and_deduplicates_results():
    job = make_job(["gpu benchmark", "mi300x benchmark"])
    search_client = FakeSearchClient(
        {
            "gpu benchmark": [
                make_header("web_001", "gpu benchmark", "https://example.com/report?utm_source=x"),
                make_header("web_002", "gpu benchmark", "https://example.com/unique"),
            ],
            "mi300x benchmark": [
                make_header("web_003", "mi300x benchmark", "https://example.com/report"),
            ],
        }
    )

    result = asyncio.run(SearcherAgent(search_client=search_client).run(job))

    assert result.job_id == "job_001"
    assert len(result.search_headers) == 2
    assert [header.result_id for header in result.search_headers] == ["res_job_001_001", "res_job_001_002"]
    assert all(header.job_id == "job_001" for header in result.search_headers)
    assert result.search_coverage.queries_run == 2
    assert result.search_coverage.results_found == 2


def test_evidence_extractor_uses_fetched_page_text_when_available():
    job = make_job(["mi300x memory"])
    header = make_header(
        "res_001",
        "mi300x memory",
        "https://example.com/mi300x",
        snippet="Snippet should not be used when page text is available.",
    )
    fetcher = FakePageFetcher(
        {
            "https://example.com/mi300x": (
                "AMD MI300X includes 192GB of HBM3 memory. "
                "This page has unrelated details too."
            )
        }
    )

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.evidence_id == "ev_job_001_001"
    assert evidence.job_id == "job_001"
    assert evidence.result_id == "res_001"
    assert evidence.source_url == "https://example.com/mi300x"
    assert evidence.source_quote == "AMD MI300X includes 192GB of HBM3 memory."
    assert evidence.claim == "AMD MI300X includes 192GB of HBM3 memory."
    assert evidence.quote_location == "page"
    assert evidence.limitations == []


def test_evidence_extractor_marks_snippet_only_evidence_with_limitation():
    job = make_job(["h100 memory"])
    header = make_header(
        "res_001",
        "h100 memory",
        "https://example.com/h100",
        snippet="NVIDIA H100 includes HBM memory.",
    )

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=FakePageFetcher({})).extract(job, [header]))

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.quote_location == "snippet"
    assert evidence.relevance_to_query < 0.5
    assert "snippet-only evidence" in evidence.limitations


def test_evidence_extractor_caps_very_long_quote_claims():
    job = make_job(["gemini agent workflow"])
    header = make_header(
        "res_001",
        "gemini agent workflow",
        "https://example.com/gemini-agents",
        snippet="Snippet should not be used.",
    )
    long_sentence = "Gemini agent workflow " + "evidence " * 120 + "supports the build decision."
    fetcher = FakePageFetcher({"https://example.com/gemini-agents": long_sentence})

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    evidence = result.evidence_items[0]
    assert len(evidence.source_quote) <= 360
    assert evidence.claim == evidence.source_quote
    assert evidence.source_quote in long_sentence


def test_evidence_extractor_skips_navigation_boilerplate_for_clean_quote():
    job = make_job(["google adk multi agent systems"])
    header = make_header(
        "res_001",
        "google adk multi agent systems",
        "https://example.com/adk",
        snippet="Snippet should not be used.",
    )
    text = (
        "Build multi-agentic systems using Google ADK | Google Cloud Blog Jump to Content Cloud Blog Contact sales. "
        "Google ADK helps developers build multi-agent systems with specialized agents and orchestration. "
        "Navigation Menu Toggle navigation Sign in."
    )
    fetcher = FakePageFetcher({"https://example.com/adk": text})

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    assert result.evidence_items[0].source_quote == (
        "Google ADK helps developers build multi-agent systems with specialized agents and orchestration."
    )


def test_evidence_extractor_skips_google_docs_header_boilerplate():
    job = make_job(["gemini agent architecture tools"])
    header = make_header(
        "res_001",
        "gemini agent architecture tools",
        "https://cloud.google.com/architecture/agents",
        snippet="Snippet should not be used.",
    )
    text = (
        "Agentic AI architecture guides | Cloud Architecture Center | Google Cloud Documentation "
        "Skip to main content Technology areas close AI and ML Application development. "
        "Gemini agents can use tools to retrieve information and take actions on behalf of users."
    )
    fetcher = FakePageFetcher({"https://cloud.google.com/architecture/agents": text})

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    assert result.evidence_items[0].source_quote == (
        "Gemini agents can use tools to retrieve information and take actions on behalf of users."
    )


def test_evidence_extractor_rejects_pdf_binary_text():
    job = make_job(["gemini long context"])
    header = make_header(
        "res_001",
        "gemini long context",
        "https://example.com/paper.pdf",
        snippet="A snippet should not become verified page evidence.",
    )
    binary_text = "%PDF-1.5 5 0 obj /Filter /FlateDecode stream x00 xff endstream endobj " * 5
    fetcher = FakePageFetcher({"https://example.com/paper.pdf": binary_text})

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    assert result.evidence_items == []
    assert result.extraction_failures[0].reason == "missing source quote"


def test_deterministic_fallback_rejects_low_relevance_page_quote():
    job = make_job(["gemini function calling"])
    header = make_header(
        "res_001",
        "gemini function calling",
        "https://example.com/statistics",
        snippet="Snippet should not be used.",
    )
    fetcher = FakePageFetcher(
        {
            "https://example.com/statistics": (
                "Cure models require specific identifiability conditions for valid parameter estimation."
            )
        }
    )

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=fetcher).extract(job, [header]))

    assert result.evidence_items == []
    assert result.extraction_failures[0].reason == "source quote failed relevance filter"


def test_llm_extraction_accepts_quote_with_normalized_whitespace_anchor():
    job = make_job(["gemini function calling"])
    header = make_header("res_001", "gemini function calling", "https://example.com/function-calling")
    source = make_source(
        header,
        "Function calling lets Gemini models connect to external tools and APIs. Extra details.",
    )
    provider = FakeExtractionLLM(
        [
            {
                "evidence_items": [
                    {
                        "result_id": "res_001",
                        "claim": "Gemini supports function calling with external tools.",
                        "source_quote": "Function   calling lets Gemini models connect to external tools and APIs.",
                        "relevance_to_query": 0.9,
                    }
                ]
            }
        ]
    )

    result = asyncio.run(EvidenceExtractorAgent(llm_provider=provider).extract(job, [header], [source]))

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.extraction_method == "llm_batch"
    assert evidence.source_quote == "Function calling lets Gemini models connect to external tools and APIs."
    assert "anchor_method:normalized" in evidence.limitations


def test_llm_extraction_rejects_unanchored_quote_and_records_failure():
    job = make_job(["gemini function calling"])
    header = make_header("res_001", "gemini function calling", "https://example.com/function-calling")
    source = make_source(header, "Function calling lets Gemini models connect to external tools and APIs.")
    provider = FakeExtractionLLM(
        [
            {
                "evidence_items": [
                    {
                        "result_id": "res_001",
                        "claim": "Gemini can book flights directly.",
                        "source_quote": "Gemini can book flights directly with no tools.",
                    }
                ]
            }
        ]
    )

    result = asyncio.run(EvidenceExtractorAgent(llm_provider=provider).extract(job, [header], [source]))

    assert result.evidence_items == []
    assert result.extraction_failures[0].reason == "llm quote could not be anchored"


def test_deterministic_fallback_records_why_llm_evidence_was_not_used():
    job = make_job(["gemini function calling"])
    header = make_header("res_001", "gemini function calling", "https://example.com/function-calling")
    source = make_source(
        header,
        "Gemini function calling lets developers connect models to external tools and APIs.",
    )
    provider = FakeExtractionLLM([{"evidence_items": []}])

    result = asyncio.run(EvidenceExtractorAgent(llm_provider=provider).extract(job, [header], [source]))

    assert len(result.evidence_items) == 1
    evidence = result.evidence_items[0]
    assert evidence.extraction_method == "deterministic_fallback"
    assert evidence.fallback_reason == "llm_returned_no_accepted_evidence: llm extraction returned no evidence"


def test_llm_extraction_assigns_unique_evidence_ids_across_sources():
    job = make_job(["gemini agent tools"])
    header_a = make_header("res_001", "gemini agent tools", "https://example.com/a")
    header_b = make_header("res_002", "gemini agent tools", "https://example.com/b")
    source_a = make_source(header_a, "Gemini agents use tools to perform useful work.")
    source_b = make_source(header_b, "Grounded agents use search results to improve answers.")
    provider = FakeExtractionLLM(
        [
            {"evidence_items": [{"result_id": "res_001", "claim": "Gemini agents use tools.", "source_quote": source_a.text}]},
            {"evidence_items": [{"result_id": "res_002", "claim": "Grounded agents use search results.", "source_quote": source_b.text}]},
        ]
    )

    result = asyncio.run(EvidenceExtractorAgent(llm_provider=provider).extract(job, [header_a, header_b], [source_a, source_b]))

    assert [item.evidence_id for item in result.evidence_items] == ["ev_job_001_001", "ev_job_001_002"]


def test_evidence_extractor_records_failure_when_no_url_or_quote_exists():
    job = make_job(["empty"])
    no_quote = make_header("res_001", "empty", "https://example.com/empty", snippet="")
    no_url = SearchHeader.model_construct(
        result_id="res_002",
        job_id="job_001",
        query="empty",
        title="Missing URL",
        url="",
        snippet="Has snippet but no URL.",
        rank=2,
        source_type_guess="unknown",
    )

    result = asyncio.run(EvidenceExtractorAgent(page_fetcher=FakePageFetcher({})).extract(job, [no_quote, no_url]))

    assert result.evidence_items == []
    assert len(result.extraction_failures) == 2
    assert {failure.result_id for failure in result.extraction_failures} == {"res_001", "res_002"}


class FakeSearchClient:
    def __init__(self, results_by_query):
        self.results_by_query = results_by_query
        self.queries = []

    async def search_many(self, queries, max_results_per_query):
        self.queries.extend(queries)
        results = []
        for query in queries:
            results.extend(self.results_by_query.get(query, []))
        return results[: max_results_per_query * max(1, len(queries))]


class FakePageFetcher:
    def __init__(self, text_by_url):
        self.text_by_url = text_by_url

    async def fetch_text(self, url):
        return self.text_by_url.get(url)


def make_job(queries):
    return ResearchJob(
        job_id="job_001",
        job_name="Benchmark evidence",
        objective="Find benchmark evidence.",
        search_queries=queries,
        source_priorities=["official", "paper"],
        must_answer=["memory", "throughput"],
        evidence_requirements={"max_results_per_query": 5},
    )


def make_header(result_id, query, url, snippet="A useful snippet."):
    return SearchHeader(
        result_id=result_id,
        job_id="web",
        query=query,
        title="Result",
        url=url,
        snippet=snippet,
        rank=1,
        source_type_guess="official",
    )


def make_source(header, text):
    return FetchedSource(
        source_id=f"src_{header.result_id}",
        result_id=header.result_id,
        url=header.url,
        title=header.title,
        text=text,
        source_type="official",
        source_quality_score=0.9,
        provider="http",
        fetch_status="fetched_http",
        success=True,
    )


class FakeExtractionLLM:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    async def chat_json(self, messages, schema, temperature, max_tokens, **kwargs):
        payload = self.payloads[self.calls]
        self.calls += 1
        return LLMResponse(
            text="{}",
            parsed_json=payload,
            model="fake",
            provider="fake",
        )
