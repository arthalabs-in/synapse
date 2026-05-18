"""FlashRank semantic reranker wrapper.

Thin adapter around `FlashRank <https://github.com/PrithivirajDamodaran/FlashRank>`_
that scores :class:`~backend.models.SearchHeader` objects against a user query
using an ONNX cross-encoder. Intentionally permissive: any failure (missing
package, model download error, malformed FlashRank response) degrades silently
to an empty score map so the lexical pre-ranker remains authoritative.

The wrapper is gated by ``config.SEMANTIC_RERANK_ENABLED`` at the call site in
``backend/reranker.py``; this module itself is inert unless called.

Testability: pass a ``client`` with a ``rerank(request)`` method matching
FlashRank's ``Ranker`` interface to avoid downloading model weights in tests.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from config import config
from backend.models import SearchHeader


class _FlashRankClientProtocol(Protocol):
    """Minimal interface we rely on from :class:`flashrank.Ranker`."""

    def rerank(self, request: Any) -> list[dict[str, Any]]: ...


class FlashRankSemanticReranker:
    """Score ``SearchHeader`` candidates against a query via FlashRank.

    Parameters
    ----------
    model_name:
        FlashRank model identifier. Defaults to ``config.SEMANTIC_RERANK_MODEL``.
    client:
        Optional pre-built ranker. Tests inject a stub; production code lets
        this default to ``None`` so a lazy singleton is built on first use.
    """

    def __init__(
        self,
        model_name: str | None = None,
        client: _FlashRankClientProtocol | None = None,
    ):
        self.model_name = (model_name or config.SEMANTIC_RERANK_MODEL or "ms-marco-TinyBERT-L-2-v2").strip()
        self._client = client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def rerank_headers(self, query: str, headers: Iterable[SearchHeader]) -> dict[str, float]:
        """Return ``{result_id: score}`` normalized to ``[0, 1]``.

        An empty dict means "semantic reranker contributed no signal" — callers
        must treat that as a soft failure and keep the lexical ordering.
        """
        header_list = [header for header in headers if getattr(header, "result_id", None)]
        if not query or not header_list:
            return {}

        passages = [
            {
                "id": header.result_id,
                "text": _passage_text(header),
                "meta": {"url": header.url, "provider": header.provider},
            }
            for header in header_list
        ]

        client = self._resolve_client()
        if client is None:
            return {}

        try:
            request = _build_rerank_request(query, passages)
            if request is None:
                return {}
            results = client.rerank(request)
        except Exception:
            # FlashRank raises on model-download / runtime errors. Never propagate.
            return {}

        return _normalize_scores(results)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve_client(self) -> _FlashRankClientProtocol | None:
        if self._client is not None:
            return self._client
        try:
            from flashrank import Ranker  # type: ignore
        except Exception:
            return None
        try:
            self._client = Ranker(model_name=self.model_name)
        except Exception:
            return None
        return self._client


def _passage_text(header: SearchHeader) -> str:
    parts = [header.title or "", header.snippet or ""]
    # Include URL domain as a weak lexical anchor; the cross-encoder still
    # dominates, but this prevents bare-title headers from being starved.
    if header.url:
        parts.append(header.url)
    return "\n".join(part for part in parts if part).strip() or header.title or header.url or " "


def _build_rerank_request(query: str, passages: list[dict[str, Any]]):
    """Construct a FlashRank ``RerankRequest`` if the package is importable."""
    try:
        from flashrank import RerankRequest  # type: ignore
    except Exception:
        return None
    try:
        return RerankRequest(query=query, passages=passages)
    except Exception:
        return None


def _normalize_scores(results: Any) -> dict[str, float]:
    if not results:
        return {}
    normalized: dict[str, float] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        rid = item.get("id")
        if rid is None:
            continue
        raw = item.get("score")
        try:
            score = float(raw)
        except (TypeError, ValueError):
            continue
        if score != score:  # NaN guard
            continue
        # FlashRank cross-encoder scores are already sigmoid outputs in [0, 1],
        # but clip defensively so downstream math never sees an out-of-band value.
        normalized[str(rid)] = max(0.0, min(1.0, score))
    return normalized


# ----------------------------------------------------------------------
# Lazy singleton for the default reranker.
# ----------------------------------------------------------------------
_default_instance: FlashRankSemanticReranker | None = None


def get_default_semantic_reranker() -> FlashRankSemanticReranker | None:
    """Return a process-wide :class:`FlashRankSemanticReranker`, or ``None``.

    Returns ``None`` when the semantic reranker flag is disabled; callers can
    treat that as a definitive "skip the semantic pass" signal without having
    to re-check the config themselves.
    """
    global _default_instance
    if not config.SEMANTIC_RERANK_ENABLED:
        return None
    if _default_instance is None:
        _default_instance = FlashRankSemanticReranker()
    return _default_instance


def reset_default_semantic_reranker() -> None:
    """Testing hook. Clears the cached singleton."""
    global _default_instance
    _default_instance = None
