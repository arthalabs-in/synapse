"""SearchHeader -> FetchedSource orchestration."""

import asyncio

from datetime import datetime, timezone
from time import perf_counter

from config import config
from backend.models import FetchedSource, SearchHeader
from backend.providers.browser.camofox_client import CamofoxClient
from backend.providers.browser.html_fetcher import HtmlFetcher
from backend.providers.sources.normalizer import domain_from_url, normalize_url
from backend.providers.sources.quality import classify_source_type, source_quality_score


class SourceFetcher:
    def __init__(
        self,
        html_fetcher: HtmlFetcher | None = None,
        camofox_client: CamofoxClient | None = None,
        min_text_chars: int = config.SOURCE_FETCH_MIN_TEXT_CHARS,
    ):
        self.html_fetcher = html_fetcher or HtmlFetcher()
        self.camofox_client = camofox_client or CamofoxClient()
        self.min_text_chars = min_text_chars
        self.cache: dict[str, FetchedSource] = {}
        self._inflight: dict[str, asyncio.Task[FetchedSource]] = {}
        self.fetch_events: list[dict] = []
        self.summary = {
            "fetched_http_count": 0,
            "fetched_camofox_count": 0,
            "arxiv_metadata_count": 0,
            "failed_count": 0,
        }

    async def fetch_many(self, headers: list[SearchHeader]) -> list[FetchedSource]:
        tasks = [self._fetch_cached(header) for header in headers]
        return await asyncio.gather(*tasks)

    async def _fetch_cached(self, header: SearchHeader) -> FetchedSource:
        key = header.arxiv_id or normalize_url(header.url)
        if key in self.cache:
            return self.cache[key]
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(self.fetch_one(header))
            self._inflight[key] = task
        try:
            source = await task
            self.cache[key] = source
            return source
        finally:
            if task.done():
                self._inflight.pop(key, None)

    async def fetch_one(self, header: SearchHeader) -> FetchedSource:
        wall_start = datetime.now(timezone.utc)
        start = perf_counter()
        if header.provider == "arxiv":
            source = self._arxiv_metadata_source(header)
            self.summary["arxiv_metadata_count"] += 1
            self._record_fetch_event(header, source, start, wall_start)
            return source

        if not config.SOURCE_FETCH_ENABLED:
            source = self._skipped(header)
            self.summary["failed_count"] += 1
            self._record_fetch_event(header, source, start, wall_start)
            return source

        source = await self.html_fetcher.fetch(header)
        if source.success and len(source.text) >= self.min_text_chars:
            self.summary["fetched_http_count"] += 1
            self._record_fetch_event(header, source, start, wall_start)
            return source
        camofox_source = await self.camofox_client.fetch(header)
        if camofox_source.success:
            self.summary["fetched_camofox_count"] += 1
            self._record_fetch_event(header, camofox_source, start, wall_start)
            return camofox_source
        if source.success and source.text:
            self.summary["fetched_http_count"] += 1
            self._record_fetch_event(header, source, start, wall_start)
            return source
        self.summary["failed_count"] += 1
        self._record_fetch_event(header, source, start, wall_start)
        return source

    def _record_fetch_event(self, header: SearchHeader, source: FetchedSource, start: float, wall_start: datetime) -> None:
        self.fetch_events.append(
            {
                "result_id": header.result_id,
                "provider": source.provider,
                "fetch_status": source.fetch_status,
                "success": source.success,
                "url": header.url,
                "seconds": round(perf_counter() - start, 6),
                "wall_start": wall_start.isoformat(),
                "wall_end": datetime.now(timezone.utc).isoformat(),
                "text_chars": len(source.text or ""),
                "error": source.error_message,
            }
        )

    def _arxiv_metadata_source(self, header: SearchHeader) -> FetchedSource:
        source_type = "paper"
        text = header.metadata.get("summary") or header.snippet
        return FetchedSource(
            source_id=f"src_{header.result_id}",
            result_id=header.result_id,
            url=header.url,
            canonical_url=normalize_url(header.url),
            title=header.title,
            domain=domain_from_url(header.url),
            text=text,
            source_type=source_type,
            source_quality_score=source_quality_score(source_type),
            provider="arxiv",
            fetch_status="arxiv_metadata_only",
            fetched_at=datetime.now(timezone.utc),
            success=bool(text),
            error_message=None if text else "arxiv metadata missing summary",
            metadata=header.metadata,
        )

    def _skipped(self, header: SearchHeader) -> FetchedSource:
        source_type = classify_source_type(header.url, header.title, header.provider)
        return FetchedSource(
            source_id=f"src_{header.result_id}",
            result_id=header.result_id,
            url=header.url,
            canonical_url=normalize_url(header.url),
            title=header.title,
            domain=domain_from_url(header.url),
            text="",
            source_type=source_type,
            source_quality_score=source_quality_score(source_type),
            provider="source_fetcher",
            fetch_status="skipped",
            fetched_at=datetime.now(timezone.utc),
            success=False,
            error_message="source fetching disabled",
            metadata={},
        )
