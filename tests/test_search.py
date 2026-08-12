import asyncio

import pytest

from backend.models import SearchHeader
from backend.search_tools import (
    SearchClient,
    SearchNoResultsError,
    SearchProviderError,
)


def test_search_web_returns_search_headers_and_guesses_source_type():
    client = SearchClient(ddg_factory=lambda: FakeDuckDuckGo())

    results = asyncio.run(client.search_web("python docs", max_results=3))

    assert results == [
        SearchHeader(
            result_id="web_001",
            job_id="web",
            query="python docs",
            title="Python Docs",
            url="https://docs.python.org/3/",
            snippet="Official Python documentation.",
            rank=1,
            source_type_guess="docs",
        )
    ]


def test_search_arxiv_returns_paper_headers():
    paper = FakePaper(
        title="Transformer Paper",
        entry_id="https://arxiv.org/abs/1706.03762",
        pdf_url="https://arxiv.org/pdf/1706.03762",
        summary="Attention is all you need.",
    )
    client = SearchClient(arxiv_client_factory=lambda: FakeArxivClient([paper]))

    results = asyncio.run(client.search_arxiv("transformer", max_results=2))

    assert results[0].query == "transformer"
    assert results[0].title == "Transformer Paper"
    assert results[0].url == "https://arxiv.org/abs/1706.03762"
    assert results[0].snippet == "Attention is all you need."
    assert results[0].rank == 1
    assert results[0].source_type_guess == "paper"


def test_search_many_deduplicates_by_normalized_url_and_preserves_first_query():
    client = SearchClient(
        ddg_factory=lambda: FakeDuckDuckGo(
            [
                {
                    "title": "NVIDIA Blog",
                    "href": "https://developer.nvidia.com/blog/example/?utm_source=x",
                    "body": "First result.",
                },
                {
                    "title": "Duplicate",
                    "href": "https://developer.nvidia.com/blog/example",
                    "body": "Duplicate result.",
                },
            ]
        ),
        arxiv_client_factory=lambda: FakeArxivClient([]),
    )

    results = asyncio.run(client.search_many(["gpu", "gpu inference"], max_results_per_query=2))

    assert len(results) == 1
    assert results[0].query == "gpu"
    assert results[0].title == "NVIDIA Blog"
    assert results[0].source_type_guess == "blog"


def test_search_web_raises_no_results_for_empty_provider_response():
    client = SearchClient(ddg_factory=lambda: FakeDuckDuckGo([]))

    with pytest.raises(SearchNoResultsError):
        asyncio.run(client.search_web("nothing", max_results=3))


def test_search_provider_errors_are_wrapped():
    client = SearchClient(ddg_factory=lambda: BrokenDuckDuckGo())

    with pytest.raises(SearchProviderError):
        asyncio.run(client.search_web("query", max_results=3))


class FakeDuckDuckGo:
    def __init__(self, results=None):
        self.results = (
            [
                {
                    "title": "Python Docs",
                    "href": "https://docs.python.org/3/",
                    "body": "Official Python documentation.",
                }
            ]
            if results is None
            else results
        )

    def text(self, query, max_results):
        assert max_results >= 1
        return self.results[:max_results]


class BrokenDuckDuckGo:
    def text(self, query, max_results):
        raise RuntimeError("provider down")


class FakeArxivClient:
    def __init__(self, papers):
        self.papers = papers

    def results(self, search):
        return self.papers


class FakePaper:
    def __init__(self, title, entry_id, pdf_url, summary):
        self.title = title
        self.entry_id = entry_id
        self.pdf_url = pdf_url
        self.summary = summary
