"""Async search provider wrappers for SYNAPSE.

Search results are headers only. Snippets are not evidence and should not be
treated as verified claims.
"""

import asyncio
from collections.abc import Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import arxiv
from duckduckgo_search import DDGS

from backend.models import SearchHeader
from backend.providers.search.arxiv_provider import ArxivProvider
from backend.providers.search.composite_search import CompositeSearchProvider
from backend.providers.search.duckduckgo_provider import DuckDuckGoProvider


class SearchProviderError(RuntimeError):
    """Raised when a search provider fails unexpectedly."""


class SearchNoResultsError(RuntimeError):
    """Raised when a provider returns no usable results."""


class SearchClient:
    """Async wrapper around DuckDuckGo and arXiv search providers."""

    def __init__(
        self,
        ddg_factory: Callable[[], object] = DDGS,
        arxiv_client_factory: Callable[[], object] = arxiv.Client,
    ):
        self._ddg_factory = ddg_factory
        self._arxiv_client_factory = arxiv_client_factory

    async def search_web(self, query: str, max_results: int = 5) -> list[SearchHeader]:
        """Search DuckDuckGo and return normalized search headers."""
        try:
            raw_results = await asyncio.to_thread(self._run_duckduckgo, query, max_results)
        except Exception as exc:
            raise SearchProviderError(f"DuckDuckGo search failed: {exc}") from exc

        headers = self._web_results_to_headers(query, raw_results)
        if not headers:
            raise SearchNoResultsError(f"No web results for query: {query}")
        return self._dedupe_headers(headers)

    async def search_arxiv(self, query: str, max_results: int = 5) -> list[SearchHeader]:
        """Search arXiv and return normalized paper headers."""
        try:
            papers = await asyncio.to_thread(self._run_arxiv, query, max_results)
        except Exception as exc:
            raise SearchProviderError(f"arXiv search failed: {exc}") from exc

        headers = self._arxiv_results_to_headers(query, papers)
        if not headers:
            raise SearchNoResultsError(f"No arXiv results for query: {query}")
        return self._dedupe_headers(headers)

    async def search_many(self, queries: Iterable[str], max_results_per_query: int = 5) -> list[SearchHeader]:
        """Run web and arXiv searches for many queries, deduplicated by URL."""
        tasks = []
        for query in queries:
            tasks.append(self.search_web(query, max_results_per_query))
            tasks.append(self.search_arxiv(query, max_results_per_query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        headers: list[SearchHeader] = []
        provider_errors: list[Exception] = []

        for result in results:
            if isinstance(result, SearchNoResultsError):
                continue
            if isinstance(result, Exception):
                provider_errors.append(result)
                continue
            headers.extend(result)

        if headers:
            return self._dedupe_headers(headers)
        if provider_errors:
            raise SearchProviderError("; ".join(str(error) for error in provider_errors))
        raise SearchNoResultsError("No results for provided queries")

    def _run_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        ddg = self._ddg_factory()
        return list(ddg.text(query, max_results=max_results))

    def _run_arxiv(self, query: str, max_results: int) -> list[object]:
        client = self._arxiv_client_factory()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        return list(client.results(search))

    def _web_results_to_headers(self, query: str, results: Iterable[dict]) -> list[SearchHeader]:
        headers = []
        for rank, result in enumerate(results, start=1):
            title = result.get("title") or ""
            url = result.get("href") or result.get("url") or ""
            snippet = result.get("body") or result.get("snippet") or ""
            if not title or not url:
                continue
            headers.append(
                SearchHeader(
                    result_id=f"web_{rank:03d}",
                    job_id="web",
                    query=query,
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=rank,
                    source_type_guess=guess_source_type(url, title),
                )
            )
        return headers

    def _arxiv_results_to_headers(self, query: str, papers: Iterable[object]) -> list[SearchHeader]:
        headers = []
        for rank, paper in enumerate(papers, start=1):
            url = getattr(paper, "entry_id", "") or getattr(paper, "pdf_url", "")
            title = getattr(paper, "title", "") or ""
            summary = getattr(paper, "summary", "") or ""
            if not title or not url:
                continue
            headers.append(
                SearchHeader(
                    result_id=f"arxiv_{rank:03d}",
                    job_id="arxiv",
                    query=query,
                    title=title,
                    url=url,
                    snippet=summary[:500],
                    rank=rank,
                    source_type_guess="paper",
                )
            )
        return headers

    def _dedupe_headers(self, headers: Iterable[SearchHeader]) -> list[SearchHeader]:
        seen = set()
        deduped = []
        for header in headers:
            normalized = normalize_url(header.url)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(header)
        return deduped


class SearchEngine(SearchClient):
    """Compatibility wrapper for older synchronous skeleton code."""

    def web_search(self, query: str, max_results: int = 5) -> list[SearchHeader]:
        try:
            return asyncio.run(self.search_web(query, max_results))
        except SearchNoResultsError:
            return []

    def arxiv_search(self, query: str, max_results: int = 5) -> list[SearchHeader]:
        try:
            return asyncio.run(self.search_arxiv(query, max_results))
        except SearchNoResultsError:
            return []

    def search(self, query: str, max_results: int = 5) -> list[SearchHeader]:
        try:
            return asyncio.run(self.search_many([query], max_results))
        except SearchNoResultsError:
            return []


def normalize_url(url: str) -> str:
    """Normalize URLs for result deduplication."""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def guess_source_type(url: str, title: str = "") -> str:
    """Best-effort source classification for routing, not evidence quality."""
    haystack = f"{url} {title}".lower()
    host = urlsplit(url).netloc.lower()

    if "arxiv.org" in host or "/paper" in haystack or "proceedings" in haystack:
        return "paper"
    if "docs." in host or "/docs" in haystack or "documentation" in haystack:
        return "docs"
    if any(token in host for token in ("reuters.com", "bloomberg.com", "apnews.com", "news.")):
        return "news"
    if "blog" in haystack or "medium.com" in host or "substack.com" in host:
        return "blog"
    if _looks_official_host(host):
        return "official"
    return "unknown"


def _looks_official_host(host: str) -> bool:
    official_domains = (
        "amd.com",
        "nvidia.com",
        "intel.com",
        "microsoft.com",
        "google.com",
        "openai.com",
        "python.org",
        "github.com",
    )
    return any(host == domain or host.endswith(f".{domain}") for domain in official_domains)


search_client = SearchClient()
search_engine = SearchEngine()


def create_default_search_provider() -> CompositeSearchProvider:
    return CompositeSearchProvider([DuckDuckGoProvider(), ArxivProvider()])
