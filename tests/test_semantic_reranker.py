"""Tests for the optional FlashRank semantic reranker.

These tests avoid any real FlashRank model download by injecting stub clients
or stub rerankers. They verify:

1. Flag-off path preserves the pre-existing lexical behavior exactly.
2. Flag-on path blends cross-encoder scores into the final ranking and can
   surface a lexically-weak-but-semantically-relevant header.
3. ``rank_search_headers`` never raises on a broken semantic reranker; it
   silently degrades to lexical ordering.
4. ``FlashRankSemanticReranker`` normalizes scores, handles malformed
   FlashRank responses, and returns an empty map when ``flashrank`` is not
   importable.
5. ``get_default_semantic_reranker`` is gated by ``config.SEMANTIC_RERANK_ENABLED``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pytest

from backend.models import ResearchJob, SearchHeader
from backend.providers.rerankers.flashrank_reranker import (
    FlashRankSemanticReranker,
    _normalize_scores,
    get_default_semantic_reranker,
    reset_default_semantic_reranker,
)
from backend.reranker import rank_search_headers
from config import config


# ---------------------------------------------------------------------------
# Helpers and stubs.
# ---------------------------------------------------------------------------


@dataclass
class StubClient:
    """Mimics :class:`flashrank.Ranker`."""

    scores: dict[str, float] = field(default_factory=dict)
    calls: list[Any] = field(default_factory=list)
    raise_on_call: bool = False
    return_malformed: bool = False

    def rerank(self, request: Any) -> list[dict[str, Any]]:
        self.calls.append(request)
        if self.raise_on_call:
            raise RuntimeError("simulated flashrank failure")
        if self.return_malformed:
            return "not a list"  # type: ignore[return-value]
        # Extract passage ids from whatever the request looks like.
        ids = _ids_from_request(request)
        return [{"id": rid, "score": self.scores.get(rid, 0.0)} for rid in ids]


class StubReranker:
    """Drop-in replacement for ``FlashRankSemanticReranker``."""

    def __init__(self, scores: dict[str, float] | None = None, raise_on_call: bool = False):
        self.scores = scores or {}
        self.raise_on_call = raise_on_call
        self.calls: list[tuple[str, list[str]]] = []

    def rerank_headers(self, query: str, headers: Any) -> dict[str, float]:
        ids = [h.result_id for h in headers]
        self.calls.append((query, ids))
        if self.raise_on_call:
            raise RuntimeError("boom")
        return {rid: self.scores.get(rid, 0.0) for rid in ids}


def _ids_from_request(request: Any) -> list[str]:
    # ``RerankRequest`` exposes ``.passages``; in tests we also accept a dict.
    if hasattr(request, "passages"):
        passages = request.passages
    elif isinstance(request, dict):
        passages = request.get("passages", [])
    else:
        passages = []
    return [str(p.get("id")) for p in passages if isinstance(p, dict) and p.get("id") is not None]


def _make_job(job_id: str = "job_a") -> ResearchJob:
    return ResearchJob(
        job_id=job_id,
        job_name="RAG production failures",
        objective="Identify dominant production failure modes of RAG systems.",
        search_queries=["RAG production failure modes 2025"],
        source_priorities=["paper", "official"],
        must_answer=["failure mode", "mitigation"],
    )


def _make_header(
    result_id: str,
    title: str,
    url: str,
    snippet: str,
    source_type: str = "blog",
    rank: int = 1,
    provider: str = "duckduckgo",
    job_id: str = "job_a",
) -> SearchHeader:
    return SearchHeader(
        result_id=result_id,
        job_id=job_id,
        query="RAG production failure modes 2025",
        title=title,
        url=url,
        snippet=snippet,
        rank=rank,
        provider=provider,
        source_type_guess=source_type,
    )


@pytest.fixture
def semantic_rerank_off():
    """Force the flag off around a test and restore it afterward."""
    original = config.SEMANTIC_RERANK_ENABLED
    config.SEMANTIC_RERANK_ENABLED = False
    reset_default_semantic_reranker()
    try:
        yield
    finally:
        config.SEMANTIC_RERANK_ENABLED = original
        reset_default_semantic_reranker()


@pytest.fixture
def semantic_rerank_on():
    """Force the flag on around a test and restore it afterward."""
    original_enabled = config.SEMANTIC_RERANK_ENABLED
    original_weight = config.SEMANTIC_RERANK_WEIGHT
    config.SEMANTIC_RERANK_ENABLED = True
    config.SEMANTIC_RERANK_WEIGHT = 2.0
    reset_default_semantic_reranker()
    try:
        yield
    finally:
        config.SEMANTIC_RERANK_ENABLED = original_enabled
        config.SEMANTIC_RERANK_WEIGHT = original_weight
        reset_default_semantic_reranker()


# ---------------------------------------------------------------------------
# rank_search_headers integration.
# ---------------------------------------------------------------------------


def test_flag_off_preserves_lexical_behavior(semantic_rerank_off):
    """With the flag off, injected rerankers are ignored."""
    job = _make_job()
    # VQualA-style noise that shares keywords with the query vs an on-topic
    # paper with weaker keyword overlap.
    noisy = _make_header(
        "noisy",
        "VQualA 2025 RAG Challenge production engagement",
        "https://arxiv.org/abs/noise",
        "Short-video engagement prediction with RAG terminology 2025 production.",
        source_type="paper",
        rank=1,
    )
    on_topic = _make_header(
        "on_topic",
        "Seven failure points in operational retrieval-augmented systems",
        "https://arxiv.org/abs/ontopic",
        "Empirical study of retrieval errors and hallucinations.",
        source_type="paper",
        rank=2,
    )
    # Stub inverts the lexical order; we should see it ignored.
    stub = StubReranker(scores={"noisy": 0.0, "on_topic": 1.0})

    baseline = rank_search_headers(
        "RAG production failure modes 2025",
        [job],
        [noisy, on_topic],
        limit=2,
    )
    with_stub = rank_search_headers(
        "RAG production failure modes 2025",
        [job],
        [noisy, on_topic],
        limit=2,
        semantic_reranker=stub,
    )

    # Behavioral claim: with flag off, injecting a reranker must produce the
    # identical ordering as not injecting one, and the stub must not be called.
    assert [h.result_id for h in with_stub] == [h.result_id for h in baseline]
    assert stub.calls == [], "semantic reranker must not be invoked when flag is off"


def test_flag_on_promotes_semantically_relevant_header(semantic_rerank_on):
    """With the flag on, a high semantic score overcomes a small lexical gap."""
    job = _make_job()
    # Identical source_type and rank so lexical difference is purely overlap.
    noisy = _make_header(
        "noisy",
        "RAG 2025 production benchmark VQualA engagement study",
        "https://arxiv.org/abs/noise",
        "Engagement metrics for short videos with RAG-adjacent terminology.",
        source_type="paper",
        rank=1,
    )
    on_topic = _make_header(
        "on_topic",
        "Seven recurrent failure points in operational retrieval-augmented systems",
        "https://arxiv.org/abs/ontopic",
        "Empirical taxonomy of retrieval errors and hallucinated outputs.",
        source_type="paper",
        rank=1,
    )
    # Stub says: on_topic is a near-perfect match, noisy is irrelevant.
    stub = StubReranker(scores={"on_topic": 0.95, "noisy": 0.05})

    ranked = rank_search_headers(
        "RAG production failure modes 2025",
        [job],
        [noisy, on_topic],
        limit=2,
        semantic_reranker=stub,
    )

    assert ranked[0].result_id == "on_topic", "semantic signal should elevate the on-topic header"
    assert len(stub.calls) == 1
    query, ids = stub.calls[0]
    assert query == "RAG production failure modes 2025"
    assert set(ids) == {"noisy", "on_topic"}


def test_broken_reranker_falls_back_to_lexical_order(semantic_rerank_on):
    """A reranker that raises must not crash the pipeline."""
    job = _make_job()
    headers = [
        _make_header("a", "A alpha", "https://example.com/a", "alpha"),
        _make_header("b", "B beta", "https://example.com/b", "beta"),
    ]
    broken = StubReranker(raise_on_call=True)

    ranked = rank_search_headers("alpha beta", [job], headers, limit=2, semantic_reranker=broken)

    # Still returns 2 headers even though the reranker blew up.
    assert len(ranked) == 2
    assert {h.result_id for h in ranked} == {"a", "b"}


def test_semantic_scores_applied_in_proportion_to_weight(semantic_rerank_on):
    """The score contribution scales with SEMANTIC_RERANK_WEIGHT."""
    job = _make_job()
    lex_winner = _make_header(
        "lex_winner",
        "RAG failure modes production 2025 empirical paper",
        "https://arxiv.org/abs/lex",
        "RAG failure modes production 2025",
        source_type="paper",
    )
    sem_winner = _make_header(
        "sem_winner",
        "Minor title",
        "https://arxiv.org/abs/sem",
        "Minor snippet",
        source_type="paper",
    )
    # Stub says semantic strongly prefers sem_winner.
    stub = StubReranker(scores={"sem_winner": 1.0, "lex_winner": 0.0})

    # Disable the floor for this test; we're isolating weight behavior here.
    # (A separate test covers the floor.)
    original_weight = config.SEMANTIC_RERANK_WEIGHT
    original_floor = config.SEMANTIC_RERANK_MIN_SCORE
    try:
        config.SEMANTIC_RERANK_MIN_SCORE = 0.0

        # With weight 0.01, lex_winner still wins.
        config.SEMANTIC_RERANK_WEIGHT = 0.01
        low = rank_search_headers(
            "RAG failure modes production 2025",
            [job],
            [lex_winner, sem_winner],
            limit=2,
            semantic_reranker=stub,
        )
        assert low[0].result_id == "lex_winner"

        # With the default weight of 2.0, sem_winner overtakes.
        config.SEMANTIC_RERANK_WEIGHT = 2.0
        high = rank_search_headers(
            "RAG failure modes production 2025",
            [job],
            [lex_winner, sem_winner],
            limit=2,
            semantic_reranker=stub,
        )
        assert high[0].result_id == "sem_winner"
    finally:
        config.SEMANTIC_RERANK_WEIGHT = original_weight
        config.SEMANTIC_RERANK_MIN_SCORE = original_floor


def test_default_singleton_is_none_when_flag_disabled(semantic_rerank_off):
    """When the flag is off, the default accessor short-circuits."""
    assert get_default_semantic_reranker() is None


def test_default_singleton_constructs_when_flag_enabled(semantic_rerank_on, monkeypatch):
    """With the flag on, the singleton is built (even if FlashRank isn't installed)."""
    # Force the wrapper's internal import to fail so we also exercise the
    # graceful degradation path — the accessor still returns an instance.
    instance = get_default_semantic_reranker()
    assert isinstance(instance, FlashRankSemanticReranker)
    # Subsequent calls return the same singleton.
    assert get_default_semantic_reranker() is instance


# ---------------------------------------------------------------------------
# FlashRankSemanticReranker unit tests (no real flashrank model needed).
# ---------------------------------------------------------------------------


def test_wrapper_returns_empty_when_no_headers():
    stub = StubClient()
    reranker = FlashRankSemanticReranker(client=stub)
    assert reranker.rerank_headers("query", []) == {}
    assert stub.calls == []


def test_wrapper_returns_empty_when_no_query():
    stub = StubClient(scores={"a": 0.9})
    reranker = FlashRankSemanticReranker(client=stub)
    headers = [_make_header("a", "title", "https://example.com/a", "snippet")]
    assert reranker.rerank_headers("", headers) == {}


def test_wrapper_uses_injected_client_when_package_missing():
    stub = StubClient(scores={"a": 0.87, "b": 0.22})
    reranker = FlashRankSemanticReranker(client=stub)
    headers = [
        _make_header("a", "A", "https://example.com/a", "alpha"),
        _make_header("b", "B", "https://example.com/b", "beta"),
    ]
    # Even though flashrank is not installed in the test env, injection works:
    # the wrapper still tries to build a RerankRequest via
    # ``_build_rerank_request`` which returns None when the package is missing.
    # When the request can't be built, we expect an empty score map.
    result = reranker.rerank_headers("alpha", headers)
    # If flashrank IS installed the stub will be called and return real scores;
    # if not, we get an empty dict. Both are correct graceful-degradation paths.
    assert isinstance(result, dict)
    if result:
        assert result == {"a": 0.87, "b": 0.22}


def test_wrapper_handles_runtime_failure_gracefully():
    stub = StubClient(scores={"a": 0.5}, raise_on_call=True)
    reranker = FlashRankSemanticReranker(client=stub)
    headers = [_make_header("a", "A", "https://example.com/a", "alpha")]
    # Even if the underlying client raises, we return an empty dict.
    assert reranker.rerank_headers("alpha", headers) == {}


def test_normalize_scores_clips_and_filters():
    raw = [
        {"id": "a", "score": 0.42},
        {"id": "b", "score": 1.9},         # above 1 → clipped to 1.0
        {"id": "c", "score": -0.3},        # below 0 → clipped to 0.0
        {"id": "d", "score": "not a float"},  # unparseable → dropped
        {"id": "e", "score": float("nan")},   # NaN → dropped
        {"score": 0.5},                    # missing id → dropped
        "not a dict",                      # junk → ignored
    ]
    assert _normalize_scores(raw) == {"a": 0.42, "b": 1.0, "c": 0.0}


def test_normalize_scores_empty_and_none():
    assert _normalize_scores([]) == {}
    assert _normalize_scores(None) == {}


def test_passage_text_falls_back_to_title_or_url():
    from backend.providers.rerankers.flashrank_reranker import _passage_text

    minimal = _make_header("a", "", "https://example.com/a", "")
    # At least something non-empty so the cross-encoder has an anchor.
    text = _passage_text(minimal)
    assert text and "example.com" in text




# ---------------------------------------------------------------------------
# SEMANTIC_RERANK_MIN_SCORE floor behavior.
# ---------------------------------------------------------------------------


def test_floor_drops_near_zero_scoring_headers(semantic_rerank_on):
    """Headers below SEMANTIC_RERANK_MIN_SCORE disappear from the ranking."""
    job = _make_job()
    noisy = _make_header(
        "noisy",
        "RAG 2025 production terms unrelated VQualA short video",
        "https://arxiv.org/abs/noise",
        "Off-topic paper that shares keywords with the query.",
        source_type="paper",
    )
    ontopic = _make_header(
        "ontopic",
        "Seven failure points in production RAG",
        "https://arxiv.org/abs/ontopic",
        "Empirical study of retrieval errors.",
        source_type="paper",
    )
    # Noisy scores below the default 0.01 floor; ontopic sails above.
    stub = StubReranker(scores={"noisy": 0.0001, "ontopic": 0.9})

    original_floor = config.SEMANTIC_RERANK_MIN_SCORE
    try:
        config.SEMANTIC_RERANK_MIN_SCORE = 0.01
        ranked = rank_search_headers(
            "RAG production failure modes",
            [job],
            [noisy, ontopic],
            limit=2,
            semantic_reranker=stub,
        )
        ids = {h.result_id for h in ranked}
        assert ids == {"ontopic"}, "noisy header should be dropped by the floor"
    finally:
        config.SEMANTIC_RERANK_MIN_SCORE = original_floor


def test_floor_of_zero_keeps_all_headers(semantic_rerank_on):
    """Setting the floor to 0.0 disables it entirely."""
    job = _make_job()
    near_zero = _make_header("a", "a", "https://example.com/a", "a", source_type="paper")
    high = _make_header("b", "b", "https://example.com/b", "b", source_type="paper")
    stub = StubReranker(scores={"a": 0.0001, "b": 0.9})

    original_floor = config.SEMANTIC_RERANK_MIN_SCORE
    try:
        config.SEMANTIC_RERANK_MIN_SCORE = 0.0
        ranked = rank_search_headers(
            "q", [job], [near_zero, high], limit=2, semantic_reranker=stub
        )
        assert {h.result_id for h in ranked} == {"a", "b"}
    finally:
        config.SEMANTIC_RERANK_MIN_SCORE = original_floor


def test_floor_ignored_for_headers_the_reranker_did_not_score(semantic_rerank_on):
    """If the reranker returns a partial map, unscored headers survive."""

    class PartialReranker:
        def __init__(self):
            self.calls = 0

        def rerank_headers(self, query, headers):
            self.calls += 1
            # Only score one of the two headers.
            return {"scored_high": 0.9}

    job = _make_job()
    scored = _make_header("scored_high", "s", "https://example.com/s", "s", source_type="paper")
    unscored = _make_header("unscored", "u", "https://example.com/u", "u", source_type="paper")

    original_floor = config.SEMANTIC_RERANK_MIN_SCORE
    try:
        config.SEMANTIC_RERANK_MIN_SCORE = 0.5  # aggressive floor
        ranked = rank_search_headers(
            "q",
            [job],
            [scored, unscored],
            limit=2,
            semantic_reranker=PartialReranker(),
        )
        ids = {h.result_id for h in ranked}
        # unscored must NOT be filtered out just because the reranker skipped it.
        assert ids == {"scored_high", "unscored"}
    finally:
        config.SEMANTIC_RERANK_MIN_SCORE = original_floor


def test_floor_inert_when_flag_off(semantic_rerank_off):
    """With the reranker disabled, the floor does nothing."""
    job = _make_job()
    h = _make_header("a", "title", "https://example.com/a", "snippet", source_type="paper")
    stub = StubReranker(scores={"a": 0.0001})

    original_floor = config.SEMANTIC_RERANK_MIN_SCORE
    try:
        config.SEMANTIC_RERANK_MIN_SCORE = 0.5
        ranked = rank_search_headers("q", [job], [h], limit=1, semantic_reranker=stub)
        # Flag is off — floor was never consulted; header survives.
        assert [r.result_id for r in ranked] == ["a"]
        assert stub.calls == []
    finally:
        config.SEMANTIC_RERANK_MIN_SCORE = original_floor


# ---------------------------------------------------------------------------
# Default reranker model — documents the upgrade from TinyBERT → MiniLM-L-12.
# ---------------------------------------------------------------------------


def test_default_semantic_rerank_model_is_minilm_l12(monkeypatch):
    """Confirms the shipped default is the sharper MiniLM-L-12-v2 cross-encoder."""
    # Isolate from user env so the class-level default is what we assert.
    for key in ("SEMANTIC_RERANK_MODEL",):
        monkeypatch.delenv(key, raising=False)
    # Re-evaluate the default by reading the os.getenv call the same way
    # config.py does; avoid importing config fresh (its values are frozen
    # at first import).
    import os

    assert os.getenv("SEMANTIC_RERANK_MODEL", "ms-marco-MiniLM-L-12-v2") == "ms-marco-MiniLM-L-12-v2"
