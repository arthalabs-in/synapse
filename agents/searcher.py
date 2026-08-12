"""Searcher agent: ResearchJob -> deduplicated SearchHeader objects."""

import asyncio
from collections.abc import Iterable

from backend.models import JobSearchOutput, ResearchJob, SearchCoverage, SearchHeader
from backend.search_tools import SearchNoResultsError, SearchProviderError, create_default_search_provider, normalize_url, search_client


class SearcherAgent:
    """Runs job search queries without summarizing, verifying, or making claims."""

    def __init__(self, search_client=None):
        self.search_client = search_client or create_default_search_provider()

    async def run(self, job: ResearchJob) -> JobSearchOutput:
        max_results = int(job.evidence_requirements.get("max_results_per_query", 5))
        errors = []

        try:
            if hasattr(self.search_client, "search_many"):
                raw_headers = await self.search_client.search_many(job.search_queries, max_results)
            elif hasattr(self.search_client, "search_web") and hasattr(self.search_client, "search_arxiv"):
                raw_headers = await self._provider_aware_search(job, max_results)
            else:
                batches = await asyncio.gather(
                    *[self.search_client.search(query, max_results=max_results) for query in job.search_queries],
                    return_exceptions=True,
                )
                raw_headers = []
                for batch in batches:
                    if isinstance(batch, Exception):
                        raise batch
                    raw_headers.extend(batch)
        except SearchNoResultsError as exc:
            raw_headers = []
            errors.append({"provider": "search", "error": str(exc)})
        except SearchProviderError as exc:
            raw_headers = []
            errors.append({"provider": "search", "error": str(exc)})

        headers = self._dedupe_and_rebind(job, raw_headers)
        coverage = SearchCoverage(
            queries_run=len(job.search_queries),
            results_found=len(headers),
            official_sources_found=sum(1 for h in headers if h.source_type_guess in {"official", "docs"}),
            academic_sources_found=sum(1 for h in headers if h.source_type_guess == "paper"),
        )

        return JobSearchOutput(
            job_id=job.job_id,
            search_headers=headers,
            search_coverage=coverage,
            search_errors=errors,
        )

    async def _provider_aware_search(self, job: ResearchJob, max_results: int) -> list[SearchHeader]:
        tasks = [self.search_client.search_web(query, max_results=max_results) for query in job.search_queries]
        if any(priority in {"paper", "academic", "arxiv"} for priority in job.source_priorities):
            tasks.append(self.search_client.search_arxiv(job.search_queries[0], max_results=min(max_results, 3)))
        batches = await asyncio.gather(*tasks, return_exceptions=True)
        raw_headers = []
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            raw_headers.extend(batch)
        return raw_headers

    def _dedupe_and_rebind(self, job: ResearchJob, headers: Iterable[SearchHeader]) -> list[SearchHeader]:
        seen = set()
        deduped = []

        for header in headers:
            normalized = normalize_url(header.url)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(
                SearchHeader(
                    result_id=f"res_{job.job_id}_{len(deduped) + 1:03d}",
                    job_id=job.job_id,
                    query=header.query,
                    title=header.title,
                    url=header.url,
                    snippet=header.snippet,
                    rank=header.rank,
                    provider=header.provider,
                    source_type_guess=header.source_type_guess,
                    metadata=header.metadata,
                    arxiv_id=header.arxiv_id,
                    pdf_url=header.pdf_url,
                    published_date=header.published_date,
                )
            )

        return deduped


async def async_execute(job: ResearchJob) -> JobSearchOutput:
    """Async compatibility entrypoint."""
    return await SearcherAgent().run(job)


def execute(job: ResearchJob) -> JobSearchOutput:
    """Synchronous compatibility entrypoint for the current skeleton."""
    return asyncio.run(async_execute(job))
