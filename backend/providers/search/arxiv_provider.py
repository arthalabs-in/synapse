"""arXiv search provider."""

import asyncio
import re
import xml.etree.ElementTree as ET

import arxiv
import httpx

from config import config
from backend.models import SearchHeader
from backend.providers.search.base import SearchProviderError


class ArxivProvider:
    provider = "arxiv"

    def __init__(self, client_factory=None):
        self.client_factory = client_factory

    async def search(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        try:
            limit = min(max_results, config.ARXIV_MAX_RESULTS)
            if self.client_factory is not None:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._search_sync, query, limit),
                    timeout=config.ARXIV_TIMEOUT_SECONDS,
                )
            return await self._search_async(query, limit)
        except Exception as exc:
            raise SearchProviderError(f"arxiv search failed: {exc}") from exc

    async def _search_async(self, query: str, max_results: int) -> list[SearchHeader]:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        async with httpx.AsyncClient(timeout=config.ARXIV_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get("https://export.arxiv.org/api/query", params=params)
            response.raise_for_status()
        return _parse_feed(query, response.text)

    def _search_sync(self, query: str, max_results: int) -> list[SearchHeader]:
        try:
            client = self.client_factory(page_size=max_results, delay_seconds=0, num_retries=0)
        except TypeError:
            client = self.client_factory()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        headers = []
        for rank, paper in enumerate(client.results(search), start=1):
            entry_id = getattr(paper, "entry_id", "") or ""
            pdf_url = getattr(paper, "pdf_url", None)
            arxiv_id = _extract_arxiv_id(entry_id or pdf_url or "")
            published = getattr(paper, "published", None)
            updated = getattr(paper, "updated", None)
            authors = [str(author) for author in getattr(paper, "authors", [])]
            categories = list(getattr(paper, "categories", []) or [])
            headers.append(
                SearchHeader(
                    result_id=f"arxiv_{arxiv_id or rank}",
                    query=query,
                    title=getattr(paper, "title", "") or "",
                    url=entry_id or pdf_url,
                    snippet=(getattr(paper, "summary", "") or "")[:800],
                    rank=rank,
                    provider=self.provider,
                    source_type_guess="paper",
                    metadata={
                        "authors": authors,
                        "summary": getattr(paper, "summary", "") or "",
                        "published": published.isoformat() if published else None,
                        "updated": updated.isoformat() if updated else None,
                        "primary_category": getattr(paper, "primary_category", None),
                        "categories": categories,
                    },
                    arxiv_id=arxiv_id,
                    pdf_url=pdf_url,
                    published_date=published.isoformat() if published else None,
                )
            )
        return headers


def _extract_arxiv_id(value: str) -> str | None:
    match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", value)
    return match.group(1) if match else None


def _parse_feed(query: str, xml_text: str) -> list[SearchHeader]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml_text)
    headers = []
    for rank, entry in enumerate(root.findall("atom:entry", ns), start=1):
        entry_id = _text(entry, "atom:id", ns)
        title = " ".join(_text(entry, "atom:title", ns).split())
        summary = " ".join(_text(entry, "atom:summary", ns).split())
        published = _text(entry, "atom:published", ns)
        updated = _text(entry, "atom:updated", ns)
        authors = [_text(author, "atom:name", ns) for author in entry.findall("atom:author", ns)]
        categories = [category.attrib.get("term", "") for category in entry.findall("atom:category", ns)]
        primary = entry.find("arxiv:primary_category", ns)
        primary_category = primary.attrib.get("term") if primary is not None else (categories[0] if categories else None)
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
                break
        arxiv_id = _extract_arxiv_id(entry_id or pdf_url or "")
        headers.append(
            SearchHeader(
                result_id=f"arxiv_{arxiv_id or rank}",
                query=query,
                title=title,
                url=entry_id or pdf_url,
                snippet=summary[:800],
                rank=rank,
                provider="arxiv",
                source_type_guess="paper",
                metadata={
                    "authors": authors,
                    "summary": summary,
                    "published": published,
                    "updated": updated,
                    "primary_category": primary_category,
                    "categories": categories,
                },
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                published_date=published,
            )
        )
    return headers


def _text(element, path: str, ns: dict[str, str]) -> str:
    found = element.find(path, ns)
    return found.text.strip() if found is not None and found.text else ""
