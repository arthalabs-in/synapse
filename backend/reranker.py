"""Deterministic ranking and context selection for live research runs."""

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from config import config
from backend.evidence_quality import build_evidence_criteria, score_source_fitness
from backend.models import FetchedSource, PlannerPrecontext, ResearchJob, SearchHeader
from backend.providers.sources.normalizer import normalize_url


SOURCE_TYPE_BOOSTS = {
    "official": 1.0,
    "documentation": 0.95,
    "docs": 0.9,
    "paper": 0.85,
    "benchmark": 0.8,
    "news": 0.45,
    "repo": 0.5,
    "blog": 0.35,
    "forum": 0.2,
    "unknown": 0.0,
}


def rank_search_headers(
    original_query: str,
    jobs: list[ResearchJob],
    headers: Iterable[SearchHeader],
    limit: int = 20,
    *,
    semantic_reranker: Any | None = None,
) -> list[SearchHeader]:
    """Rank and cap search headers before fetch/extraction.

    When ``config.SEMANTIC_RERANK_ENABLED`` is true, a cross-encoder score from
    ``semantic_reranker`` (or the default FlashRank singleton) is blended into
    the lexical score via ``config.SEMANTIC_RERANK_WEIGHT``. Headers scored
    below ``config.SEMANTIC_RERANK_MIN_SCORE`` are dropped outright (the floor
    is ignored for headers the reranker didn't score, e.g. on empty-response
    degradation). Any failure in the semantic path silently falls back to
    lexical-only ordering.
    """
    job_by_id = {job.job_id: job for job in jobs}
    deduped: list[SearchHeader] = []
    seen = set()
    for header in headers:
        key = header.arxiv_id or normalize_url(header.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(header)

    semantic_scores = _semantic_header_scores(original_query, deduped, semantic_reranker)
    floor = max(0.0, float(getattr(config, "SEMANTIC_RERANK_MIN_SCORE", 0.0) or 0.0))

    ranked = []
    lexical_ranked = []
    for header in deduped:
        job = job_by_id.get(header.job_id)
        score = _header_score(original_query, job, header)
        lexical_ranked.append((score, header.rank, header))
        if semantic_scores:
            sem = semantic_scores.get(header.result_id)
            if sem is not None:
                # Floor is only applied when the reranker actually scored this
                # header; missing scores (reranker returned partial results)
                # fall back to lexical-only behavior.
                if floor > 0.0 and sem < floor:
                    continue
                score += sem * config.SEMANTIC_RERANK_WEIGHT
        ranked.append((score, header.rank, header))
    if not ranked and lexical_ranked:
        ranked = lexical_ranked
    ranked.sort(key=lambda item: (-item[0], item[1], item[2].result_id))
    lexical_ranked.sort(key=lambda item: (-item[0], item[1], item[2].result_id))
    selected = [header for _, _, header in ranked[:limit]]
    return _ensure_header_coverage_by_job(selected, lexical_ranked or ranked, jobs, limit)


def _semantic_header_scores(
    original_query: str,
    headers: list[SearchHeader],
    semantic_reranker: Any | None,
) -> dict[str, float]:
    """Resolve and invoke the semantic reranker; never raise."""
    if not headers or not config.SEMANTIC_RERANK_ENABLED:
        return {}
    reranker = semantic_reranker
    if reranker is None:
        try:
            from backend.providers.rerankers.flashrank_reranker import (
                get_default_semantic_reranker,
            )

            reranker = get_default_semantic_reranker()
        except Exception:
            return {}
    if reranker is None:
        return {}
    try:
        result = reranker.rerank_headers(original_query, headers)
    except Exception:
        return {}
    return dict(result) if isinstance(result, dict) else {}


def rank_fetched_sources(
    original_query: str,
    jobs: list[ResearchJob],
    sources: Iterable[FetchedSource],
    headers: Iterable[SearchHeader],
    limit: int = 10,
) -> list[FetchedSource]:
    """Rank fetched sources before LLM extraction."""
    header_by_result = {header.result_id: header for header in headers}
    job_by_id = {job.job_id: job for job in jobs}
    planner_stub = _planner_stub(original_query, jobs)
    ranked = []
    seen = set()
    for source in sources:
        if not source.success or not source.text:
            continue
        if _is_thin_source(source):
            continue
        key = normalize_url(source.url)
        if key in seen:
            continue
        seen.add(key)
        header = header_by_result.get(source.result_id)
        job = job_by_id.get(header.job_id) if header else None
        query_text = " ".join([original_query, job.objective if job else "", *(job.must_answer if job else [])])
        lexical_score = _overlap_score(query_text, " ".join([source.title or "", source.text[:4000]]))
        source_type_boost = SOURCE_TYPE_BOOSTS.get(source.source_type, 0.0)
        fitness = score_source_fitness(original_query, planner_stub, source)
        score = (0.45 * lexical_score) + (0.35 * source.source_quality_score) + (0.20 * float(fitness["score"]))
        score += source_type_boost * 0.25
        if source.fetch_status == "arxiv_metadata_only":
            score += 0.15
        metadata = dict(source.metadata)
        metadata["source_fitness"] = fitness
        ranked.append((score, source.model_copy(update={"metadata": metadata})))
    ranked.sort(key=lambda item: (-item[0], item[1].source_id))
    return [source for _, source in ranked[:limit]]


def _planner_stub(original_query: str, jobs: list[ResearchJob]) -> PlannerPrecontext:
    coverage = []
    for job in jobs:
        coverage.extend(job.must_answer)
    planner = PlannerPrecontext(
        original_query=original_query,
        query_interpretation=original_query,
        precontext_claims=[],
        research_jobs=jobs,
        coverage_checklist=list(dict.fromkeys(coverage)),
    )
    planner.evidence_criteria = build_evidence_criteria(original_query, planner)
    return planner


def _is_thin_source(source: FetchedSource) -> bool:
    if source.fetch_status == "arxiv_metadata_only":
        return False
    return len((source.text or "").split()) < 40


def select_source_context(source: FetchedSource, job: ResearchJob, token_budget: int = 2000) -> str:
    return _select_relevant_context(source.text, job, token_budget)


def select_deep_review_context(source: FetchedSource, job: ResearchJob, token_budget: int = 20000) -> str:
    return _select_relevant_context(source.text, job, token_budget)


def _header_score(original_query: str, job: ResearchJob | None, header: SearchHeader) -> float:
    query_text = " ".join(
        [
            original_query,
            job.objective if job else "",
            " ".join(job.must_answer) if job else "",
            " ".join(job.source_priorities) if job else "",
        ]
    )
    candidate_text = " ".join([header.title, header.snippet, header.query])
    score = _overlap_score(query_text, candidate_text) * 3
    score += SOURCE_TYPE_BOOSTS.get(header.source_type_guess, 0.0)
    score += max(0.0, 0.6 - (header.rank - 1) * 0.05)
    if header.provider == "arxiv":
        score += 0.15
    if _published_year(header.published_date) and _published_year(header.published_date) >= 2023:
        score += 0.2
    return score


def _ensure_header_coverage_by_job(
    selected: list[SearchHeader],
    ranked: list[tuple[float, int, SearchHeader]],
    jobs: list[ResearchJob],
    limit: int,
) -> list[SearchHeader]:
    if limit <= 0 or limit < len(jobs):
        return selected

    selected_ids = {header.result_id for header in selected}
    selected_jobs = {header.job_id for header in selected}
    candidates_by_job: dict[str, SearchHeader] = {}
    for _, _, header in ranked:
        if header.job_id not in candidates_by_job:
            candidates_by_job[header.job_id] = header

    for job in jobs:
        if job.job_id in selected_jobs or job.job_id not in candidates_by_job:
            continue
        candidate = candidates_by_job[job.job_id]
        if candidate.result_id in selected_ids:
            continue
        if len(selected) < limit:
            selected.append(candidate)
            selected_ids.add(candidate.result_id)
            selected_jobs.add(candidate.job_id)
            continue
        replace_index = _lowest_replaceable_header_index(selected, protected_job_ids=selected_jobs - {candidate.job_id})
        if replace_index is None:
            continue
        removed = selected[replace_index]
        selected_ids.discard(removed.result_id)
        selected[replace_index] = candidate
        selected_ids.add(candidate.result_id)
        selected_jobs.add(candidate.job_id)
    return selected


def _lowest_replaceable_header_index(selected: list[SearchHeader], protected_job_ids: set[str]) -> int | None:
    job_counts: dict[str, int] = {}
    for header in selected:
        job_counts[header.job_id] = job_counts.get(header.job_id, 0) + 1
    for index in range(len(selected) - 1, -1, -1):
        header = selected[index]
        if header.job_id in protected_job_ids and job_counts.get(header.job_id, 0) <= 1:
            continue
        if job_counts.get(header.job_id, 0) > 1:
            return index
    return None


def _select_relevant_context(text: str, job: ResearchJob, token_budget: int) -> str:
    if not text:
        return ""
    max_chars = max(1, token_budget * 4)
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]
    job_terms = _terms(" ".join([job.objective, *job.search_queries, *job.must_answer]))
    ranked = sorted(sentences, key=lambda sentence: len(_terms(sentence) & job_terms), reverse=True)
    selected = []
    total = 0
    for sentence in ranked:
        if total + len(sentence) > max_chars:
            continue
        selected.append(sentence)
        total += len(sentence) + 1
        if total >= max_chars:
            break
    return " ".join(selected) or cleaned[:max_chars]


def _overlap_score(left: str, right: str) -> float:
    left_terms = _terms(left)
    right_terms = _terms(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / max(1, min(len(left_terms), 20))


def _terms(text: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "are",
        "what",
        "between",
        "practical",
        "tradeoffs",
        "workloads",
    }
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(term) > 2 and term not in stopwords
    }


def _published_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        match = re.search(r"\b(20\d{2})\b", value)
        return int(match.group(1)) if match else None
