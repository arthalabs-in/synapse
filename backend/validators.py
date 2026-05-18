"""Reusable validation helpers for SYNAPSE pipeline contracts."""

from collections.abc import Iterable
from typing import Any


def require_url(value: str, field_name: str = "url") -> str:
    """Return a stripped HTTP(S) URL or raise a clear validation error.

    Phase 3.2: ``upload://<hash>`` URLs are accepted when
    ``config.MULTIMODAL_ENABLED`` is True, so user-uploaded evidence can be
    represented on ``EvidenceItem`` without breaking the strict URL contract.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a URL string")

    url = value.strip()
    if url.startswith(("http://", "https://")):
        return url

    if url.startswith("upload://"):
        try:
            from config import config as _config  # local import to avoid cycles at module load time

            if getattr(_config, "MULTIMODAL_ENABLED", False):
                return url
        except Exception:
            pass

    raise ValueError(f"{field_name} must start with http:// or https://")


def require_source_quote(value: str, field_name: str = "source_quote") -> str:
    """Return a stripped quote or raise if evidence lacks source text."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def validate_planner_citations(precontext_claims: Iterable[Any]) -> None:
    """Require planner precontext claims to include claim text, source id, and URL."""
    claims = list(precontext_claims)
    if not claims:
        raise ValueError("precontext claims must include at least one cited source")

    for claim in claims:
        claim_text = _get_value(claim, "claim")
        source_id = _get_value(claim, "source_id")
        url = _get_value(claim, "url")
        if not claim_text or not source_id:
            raise ValueError("precontext claims must include claim and source_id")
        require_url(url, "precontext url")


def validate_fact_ids(known_fact_ids: Iterable[str], used_fact_ids: Iterable[str], context: str = "payload") -> None:
    """Raise when a report or patch references fact ids outside the ledger."""
    known = set(known_fact_ids)
    unknown = sorted(set(used_fact_ids) - known)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"{context} references unknown fact id(s): {joined}")


def validate_report_has_citations(report: Any) -> None:
    """Require every report section with content to include at least one citation."""
    sections = getattr(report, "sections", [])
    for section in sections:
        content = _get_value(section, "content")
        citations = _get_value(section, "citations") or []
        if content and not citations:
            section_id = _get_value(section, "section_id") or "unknown"
            raise ValueError(f"report section {section_id} must include citations")


def _get_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)
