"""Basic public HTTP source fetcher."""

import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from config import config
from backend.models import FetchedSource, SearchHeader
from backend.providers.sources.cleaner import clean_source_text
from backend.providers.sources.normalizer import domain_from_url, normalize_url
from backend.providers.sources.quality import classify_source_type, source_quality_score

try:
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None


class HtmlFetcher:
    provider = "http"

    def __init__(self, timeout_seconds: float = config.SOURCE_FETCH_TIMEOUT_SECONDS, max_chars: int = config.SOURCE_FETCH_MAX_CHARS):
        self.timeout_seconds = timeout_seconds
        self.max_chars = max_chars

    async def fetch(self, header: SearchHeader) -> FetchedSource:
        source_type = classify_source_type(header.url, header.title, header.provider)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(header.url, headers={"User-Agent": "SYNAPSE research bot"})
                response.raise_for_status()
                extracted_text = extract_text(response.text)
                cleaned = clean_source_text(extracted_text, url=header.url, title=header.title)
                text = cleaned.text[: self.max_chars]
                success = bool(text.strip())
                return FetchedSource(
                    source_id=f"src_{header.result_id}",
                    result_id=header.result_id,
                    url=header.url,
                    canonical_url=normalize_url(str(response.url)),
                    title=header.title,
                    domain=domain_from_url(header.url),
                    text=text,
                    markdown=None,
                    source_type=source_type,
                    source_quality_score=source_quality_score(source_type),
                    provider=self.provider,
                    fetch_status="fetched_http" if success else "failed",
                    fetched_at=datetime.now(timezone.utc),
                    success=success,
                    error_message=None if success else "empty extracted text",
                    metadata={
                        "status_code": response.status_code,
                        "raw_text_chars": cleaned.raw_text_chars,
                        "clean_text_chars": cleaned.clean_text_chars,
                        "removed_noise_markers": cleaned.removed_noise_markers,
                        "failed_quality_filter": cleaned.failed_quality_filter,
                        "cleaning_method": cleaned.cleaning_method,
                    },
                )
        except Exception as exc:
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
                provider=self.provider,
                fetch_status="failed",
                fetched_at=datetime.now(timezone.utc),
                success=False,
                error_message=str(exc),
                metadata={},
            )


def extract_text(html: str) -> str:
    if trafilatura:
        extracted = trafilatura.extract(html)
        if extracted:
            return " ".join(extracted.split())
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
