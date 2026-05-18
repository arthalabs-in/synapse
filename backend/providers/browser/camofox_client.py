"""Optional Camofox REST client.

CAMOFOX_FETCH_PATH is intentionally configurable because deployments may expose
different fetch/snapshot routes.
"""

from datetime import datetime, timezone

import httpx

from config import config
from backend.models import FetchedSource, SearchHeader
from backend.providers.sources.normalizer import domain_from_url, normalize_url
from backend.providers.sources.quality import classify_source_type, source_quality_score


class CamofoxClient:
    provider = "camofox"

    def __init__(
        self,
        enabled: bool = config.CAMOFOX_ENABLED,
        base_url: str = config.CAMOFOX_BASE_URL,
        health_path: str = config.CAMOFOX_HEALTH_PATH,
        fetch_path: str = config.CAMOFOX_FETCH_PATH,
        timeout_seconds: float = config.CAMOFOX_TIMEOUT_SECONDS,
    ):
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self.health_path = health_path
        self.fetch_path = fetch_path
        self.timeout_seconds = timeout_seconds

    async def health(self) -> bool:
        if not self.enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.base_url}{self.health_path}")
                return response.status_code < 400
        except httpx.HTTPError:
            return False

    async def fetch(self, header: SearchHeader) -> FetchedSource:
        source_type = classify_source_type(header.url, header.title, header.provider)
        if not self.enabled or not self.fetch_path:
            return _failed(header, source_type, "camofox disabled or CAMOFOX_FETCH_PATH unset")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}{self.fetch_path}", json={"url": header.url})
                response.raise_for_status()
                data = response.json()
                text = data.get("text") or data.get("content") or data.get("markdown") or ""
                return FetchedSource(
                    source_id=f"src_{header.result_id}",
                    result_id=header.result_id,
                    url=header.url,
                    canonical_url=data.get("canonical_url") or normalize_url(header.url),
                    title=data.get("title") or header.title,
                    domain=domain_from_url(header.url),
                    text=text,
                    markdown=data.get("markdown"),
                    source_type=source_type,
                    source_quality_score=source_quality_score(source_type),
                    provider=self.provider,
                    fetch_status="fetched_camofox" if text else "failed",
                    fetched_at=datetime.now(timezone.utc),
                    success=bool(text),
                    error_message=None if text else "empty Camofox response text",
                    metadata=data.get("metadata", {}),
                )
        except Exception as exc:
            return _failed(header, source_type, str(exc))


def _failed(header: SearchHeader, source_type: str, message: str) -> FetchedSource:
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
        provider="camofox",
        fetch_status="failed",
        fetched_at=datetime.now(timezone.utc),
        success=False,
        error_message=message,
        metadata={},
    )
