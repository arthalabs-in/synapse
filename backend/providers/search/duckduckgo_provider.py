"""DuckDuckGo/DDGS search provider."""

import asyncio
import json
import sys
import threading
from itertools import count

from config import config
from backend.models import SearchHeader
from backend.providers.search.base import SearchProviderError
from backend.providers.sources.quality import classify_source_type

try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - fallback for older dependency
    from duckduckgo_search import DDGS


class DuckDuckGoProvider:
    provider = "duckduckgo"

    def __init__(
        self,
        region: str = config.DDGS_REGION,
        safesearch: str = config.DDGS_SAFESEARCH,
        timeout_seconds: float = config.DDGS_TIMEOUT_SECONDS,
        ddgs_factory=DDGS,
    ):
        self.region = region
        self.safesearch = safesearch
        self.timeout_seconds = timeout_seconds
        self.ddgs_factory = ddgs_factory

    async def search(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        try:
            if self.ddgs_factory is DDGS:
                return await self._search_in_subprocess(query, max_results)
            return await asyncio.wait_for(self._search_in_worker(query, max_results), timeout=self.timeout_seconds)
        except Exception as exc:
            raise SearchProviderError(f"duckduckgo search failed: {exc}") from exc

    async def _search_in_subprocess(self, query: str, max_results: int) -> list[SearchHeader]:
        code = (
            "import json, sys\n"
            "try:\n"
            "    from ddgs import DDGS\n"
            "except ImportError:\n"
            "    from duckduckgo_search import DDGS\n"
            "query, region, safesearch, max_results = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])\n"
            "with DDGS() as ddgs:\n"
            "    results = list(ddgs.text(query, region=region, safesearch=safesearch, max_results=max_results))\n"
            "print(json.dumps(results), flush=True)\n"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            query,
            self.region,
            self.safesearch,
            str(max_results),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise TimeoutError("duckduckgo subprocess timed out") from exc
        if process.returncode != 0:
            message = stderr.decode(errors="replace").strip()
            raise SearchProviderError(message or f"duckduckgo subprocess exited with {process.returncode}")
        try:
            results = json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise SearchProviderError("duckduckgo subprocess returned invalid JSON") from exc
        return self._results_to_headers(query, results)

    async def _search_in_worker(self, query: str, max_results: int) -> list[SearchHeader]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[SearchHeader]] = loop.create_future()

        def set_result(result: list[SearchHeader]) -> None:
            if not future.done():
                future.set_result(result)

        def set_exception(exc: BaseException) -> None:
            if not future.done():
                future.set_exception(exc)

        def target() -> None:
            try:
                result = self._search_sync(query, max_results)
            except BaseException as exc:
                loop.call_soon_threadsafe(set_exception, exc)
            else:
                loop.call_soon_threadsafe(set_result, result)

        thread = threading.Thread(target=target, name="synapse-ddgs-search", daemon=True)
        thread.start()
        return await future

    def _search_sync(self, query: str, max_results: int) -> list[SearchHeader]:
        with self.ddgs_factory() as ddgs:
            results = ddgs.text(
                query,
                region=self.region,
                safesearch=self.safesearch,
                max_results=max_results,
            )
            return self._results_to_headers(query, results)

    def _results_to_headers(self, query: str, results) -> list[SearchHeader]:
        headers = []
        for rank, result in zip(count(1), results):
            title = result.get("title") or ""
            url = result.get("href") or result.get("url") or ""
            snippet = result.get("body") or result.get("snippet") or ""
            if not title or not url:
                continue
            source_type = classify_source_type(url, title, self.provider)
            headers.append(
                SearchHeader(
                    result_id=f"ddg_{abs(hash((query, url))) % 10_000_000}_{rank}",
                    query=query,
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=rank,
                    provider=self.provider,
                    source_type_guess=source_type,
                    metadata={"region": self.region, "safesearch": self.safesearch},
                )
            )
        return headers
