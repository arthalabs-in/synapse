"""Phase 3.2: multimodal ingestor agent.

Converts a list of user-uploaded files into quote-anchored
:class:`~backend.models.EvidenceItem` objects by asking Gemini to extract a
single verbatim passage per file. Gated by ``MULTIMODAL_ENABLED``; the research
engine refuses to call this module unless the flag is on.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from backend.models import EvidenceItem, UploadMetadata


_EXTRACTION_PROMPT = (
    "You are ingesting a file the user attached to a research query. "
    "Extract one short VERBATIM passage (1-3 sentences, max 400 chars) from the file "
    "that a researcher could later cite. Also produce a concise claim that the passage supports, "
    "the document's apparent date ('unknown' if absent), and a relevance score in [0,1]. "
    "Return strict JSON matching the schema. No markdown."
)


class _IngestedEvidence(BaseModel):
    claim: str
    source_quote: str
    source_title: str
    date: str = "unknown"
    relevance_to_query: float = 0.5
    limitations: list[str] = []


@dataclass
class MultimodalIngestResult:
    evidence_items: list[EvidenceItem]
    upload_metadata: list[UploadMetadata]


class MultimodalIngestorAgent:
    """Gemini-backed multimodal ingestor."""

    def __init__(self, llm_provider: Any | None = None):
        self.llm_provider = llm_provider

    async def ingest(
        self,
        research_question: str,
        uploads: list[dict[str, Any]],
    ) -> MultimodalIngestResult:
        evidence_items: list[EvidenceItem] = []
        upload_metadata: list[UploadMetadata] = []

        for index, upload in enumerate(uploads or []):
            data = upload.get("data") or b""
            if isinstance(data, str):
                data = data.encode("utf-8", errors="ignore")
            sha = upload.get("sha256") or hashlib.sha256(data).hexdigest()
            mime = upload.get("mime_type") or "application/octet-stream"
            file_name = upload.get("file_name") or f"upload_{index}"
            size_bytes = int(upload.get("size_bytes") or len(data))

            try:
                metadata = UploadMetadata(
                    file_name=file_name,
                    sha256=sha,
                    mime_type=mime,
                    size_bytes=size_bytes,
                )
            except Exception:
                continue
            upload_metadata.append(metadata)

            evidence = await self._ingest_one(research_question, upload, metadata, index)
            if evidence is not None:
                evidence_items.append(evidence)

        return MultimodalIngestResult(evidence_items=evidence_items, upload_metadata=upload_metadata)

    async def _ingest_one(
        self,
        research_question: str,
        upload: dict[str, Any],
        metadata: UploadMetadata,
        index: int,
    ) -> EvidenceItem | None:
        if not self.llm_provider or not hasattr(self.llm_provider, "chat_multimodal"):
            return None

        messages = [
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Research question: {research_question}\n"
                    f"File name: {metadata.file_name}\n"
                    "Extract one quote-anchored evidence entry per the schema."
                ),
            },
        ]

        try:
            response = await self.llm_provider.chat_multimodal(
                messages,
                inline_parts=[{"mime_type": metadata.mime_type, "data": upload.get("data") or b""}],
                temperature=0,
                max_tokens=1200,
            )
        except Exception:
            return None

        payload = response.parsed_json if getattr(response, "parsed_json", None) else _parse_loose_json(response.text)
        if not payload:
            return None

        try:
            ingested = _IngestedEvidence.model_validate(payload)
        except Exception:
            return None

        if not ingested.source_quote.strip():
            return None

        return EvidenceItem(
            evidence_id=f"ev_upload_{metadata.sha256[:8]}_{index}",
            job_id="uploads",
            result_id=f"upload_{metadata.sha256[:8]}",
            claim=ingested.claim.strip() or ingested.source_quote.strip()[:200],
            source_title=ingested.source_title.strip() or metadata.file_name,
            source_url=f"upload://{metadata.sha256}",
            source_quote=ingested.source_quote.strip()[:4000],
            fetched_source_id=f"upload_src_{metadata.sha256[:8]}",
            quote_location="page",
            source_type="user_upload",
            source_quality_score=0.5,
            extraction_method="llm_multimodal",
            fallback_reason=None,
            date=ingested.date or "unknown",
            relevance_to_query=max(0.0, min(1.0, float(ingested.relevance_to_query or 0.5))),
            limitations=list(ingested.limitations or []),
        )


def _parse_loose_json(text: str) -> dict[str, Any] | None:
    import json

    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            return None
