"""Composite search provider."""

import asyncio
from datetime import datetime, timezone
from time import perf_counter

from backend.models import SearchHeader
from backend.providers.search.base import SearchProvider
from backend.providers.sources.normalizer import normalize_url


class CompositeSearchProvider:
    provider = "composite"

    def __init__(self, providers: list[SearchProvider]):
        self.providers = providers
        self.last_errors: list[str] = []
        self.search_events: list[dict] = []

    async def search(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        self.last_errors = []
        results = await asyncio.gather(
            *[self._profile_provider_search(provider, query, max_results, **kwargs) for provider in self.providers],
            return_exceptions=True,
        )
        headers: list[SearchHeader] = []
        for result in results:
            if isinstance(result, Exception):
                self.last_errors.append(str(result))
            else:
                headers.extend(result)
        return self._dedupe(headers)[:max_results]

    async def _profile_provider_search(self, provider: SearchProvider, query: str, max_results: int = 5, **kwargs):
        wall_start = datetime.now(timezone.utc)
        start = perf_counter()
        provider_name = getattr(provider, "provider", provider.__class__.__name__)
        try:
            results = await provider.search(query, max_results=max_results, **kwargs)
            self.search_events.append(
                {
                    "provider": provider_name,
                    "query": query,
                    "max_results": max_results,
                    "result_count": len(results),
                    "seconds": round(perf_counter() - start, 6),
                    "wall_start": wall_start.isoformat(),
                    "wall_end": datetime.now(timezone.utc).isoformat(),
                    "ok": True,
                }
            )
            return results
        except Exception as exc:
            self.search_events.append(
                {
                    "provider": provider_name,
                    "query": query,
                    "max_results": max_results,
                    "result_count": 0,
                    "seconds": round(perf_counter() - start, 6),
                    "wall_start": wall_start.isoformat(),
                    "wall_end": datetime.now(timezone.utc).isoformat(),
                    "ok": False,
                    "error": str(exc)[:500],
                }
            )
            raise

    def _dedupe(self, headers: list[SearchHeader]) -> list[SearchHeader]:
        seen = set()
        ranked = []
        for header in sorted(headers, key=lambda item: (item.rank, item.provider)):
            key = header.arxiv_id or normalize_url(header.url)
            if key in seen:
                continue
            seen.add(key)
            ranked.append(header)
        return ranked

    async def search_web(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        return await self._search_subset(
            [provider for provider in self.providers if getattr(provider, "provider", "") != "arxiv"],
            query,
            max_results,
            **kwargs,
        )

    async def search_arxiv(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        return await self._search_subset(
            [provider for provider in self.providers if getattr(provider, "provider", "") == "arxiv"],
            query,
            max_results,
            **kwargs,
        )

    async def _search_subset(self, providers: list[SearchProvider], query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        if not providers:
            return []
        results = await asyncio.gather(
            *[self._profile_provider_search(provider, query, max_results, **kwargs) for provider in providers],
            return_exceptions=True,
        )
        headers = []
        for result in results:
            if isinstance(result, Exception):
                self.last_errors.append(str(result))
            else:
                headers.extend(result)
        return self._dedupe(headers)[:max_results]
