"""Evidence extractor: SearchHeader objects -> atomic EvidenceItem objects."""

import asyncio
from collections import defaultdict
import re
from collections.abc import Iterable

import httpx
from pydantic import BaseModel, Field

from config import config
from backend.evidence_quality import build_evidence_criteria, score_evidence_fitness
from backend.models import EvidenceItem, ExtractionFailure, FetchedSource, JobEvidenceOutput, JobSearchOutput, PlannerPrecontext, ResearchJob, SearchHeader
from backend.providers.sources.cleaner import clean_source_text
from backend.reranker import select_deep_review_context, select_source_context


class PageFetcher:
    """Small async page text fetcher used before falling back to snippets."""

    async def fetch_text(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return _strip_html(response.text)
        except httpx.HTTPError:
            return None


class EvidenceExtractorAgent:
    """Extracts atomic, quoted evidence without drawing final conclusions."""

    def __init__(self, page_fetcher: PageFetcher | None = None, llm_provider=None):
        self.page_fetcher = page_fetcher or PageFetcher()
        self.llm_provider = llm_provider

    async def extract(
        self,
        job: ResearchJob,
        search_headers: list[SearchHeader] | JobSearchOutput,
        fetched_sources: list[FetchedSource] | None = None,
    ) -> JobEvidenceOutput:
        headers = search_headers.search_headers if isinstance(search_headers, JobSearchOutput) else search_headers
        source_by_result = {source.result_id: source for source in (fetched_sources or [])}
        evidence_items: list[EvidenceItem] = []
        failures: list[ExtractionFailure] = []
        processed_result_ids: set[str] = set()
        llm_attempted_result_ids: set[str] = set()
        llm_failure_reasons_by_result: dict[str, list[str]] = defaultdict(list)

        if self.llm_provider and fetched_sources:
            extracted, llm_failures, blocked_fallback_result_ids, llm_attempted_result_ids = await self._extract_batch_with_llm(
                job, headers, fetched_sources
            )
            evidence_items.extend(extracted)
            failures.extend(llm_failures)
            for failure in llm_failures:
                llm_failure_reasons_by_result[failure.result_id].append(failure.reason)
            processed_result_ids = {item.result_id for item in extracted}
            processed_result_ids.update(blocked_fallback_result_ids)

        for header in headers:
            if header.result_id in processed_result_ids:
                continue
            if not getattr(header, "url", ""):
                failures.append(ExtractionFailure(result_id=header.result_id, reason="missing source URL"))
                continue

            fetched = source_by_result.get(header.result_id)
            page_text = fetched.text if fetched and fetched.success else await self.page_fetcher.fetch_text(header.url)
            if page_text:
                cleaned = clean_source_text(page_text, url=header.url, title=header.title)
                page_text = cleaned.text
                if cleaned.failed_quality_filter:
                    failures.append(ExtractionFailure(result_id=header.result_id, reason="source text failed quality filter"))
                    continue
            unusable_page_text = False
            if page_text and _looks_unusable_source_text(page_text):
                unusable_page_text = True
                page_text = None
            if unusable_page_text:
                failures.append(ExtractionFailure(result_id=header.result_id, reason="missing source quote"))
                continue
            quote_location = "page" if page_text else "snippet"
            source_text = page_text or header.snippet
            quote = self._extract_quote(source_text, job)

            if not quote:
                failures.append(ExtractionFailure(result_id=header.result_id, reason="missing source quote"))
                continue

            limitations = []
            relevance = self._relevance_score(job, quote)
            if quote_location == "page" and relevance < 0.2:
                failures.append(ExtractionFailure(result_id=header.result_id, reason="source quote failed relevance filter"))
                continue
            if quote_location == "snippet":
                limitations.extend(["snippet_only", "snippet-only evidence"])
                relevance = min(relevance, 0.4)

            evidence_items.append(
                self._with_evidence_fit(
                    job,
                    EvidenceItem(
                    evidence_id=f"ev_{job.job_id}_{len(evidence_items) + 1:03d}",
                    job_id=job.job_id,
                    result_id=header.result_id,
                    fetched_source_id=fetched.source_id if fetched else None,
                    claim=quote,
                    source_title=header.title,
                    source_url=header.url,
                    source_quote=quote,
                    quote_location=quote_location,
                    source_type=fetched.source_type if fetched else header.source_type_guess,
                    source_quality_score=fetched.source_quality_score if fetched else 0.0,
                    extraction_method="deterministic_fallback",
                    fallback_reason=self._fallback_reason(
                        header.result_id,
                        llm_attempted_result_ids,
                        llm_failure_reasons_by_result,
                        has_llm_provider=bool(self.llm_provider),
                        has_fetched_sources=bool(fetched_sources),
                    ),
                    relevance_to_query=relevance,
                    limitations=limitations,
                    ),
                )
            )

        for index, item in enumerate(evidence_items, start=1):
            item.evidence_id = f"ev_{job.job_id}_{index:03d}"

        return JobEvidenceOutput(
            job_id=job.job_id,
            evidence_items=evidence_items,
            extraction_failures=failures,
        )

    async def _extract_batch_with_llm(
        self,
        job: ResearchJob,
        headers: list[SearchHeader],
        fetched_sources: list[FetchedSource],
    ) -> tuple[list[EvidenceItem], list[ExtractionFailure], set[str], set[str]]:
        header_by_result = {header.result_id: header for header in headers}
        sources = [source for source in fetched_sources if source.success and source.text and source.result_id in header_by_result]
        if not sources:
            return [], [], set(), set()
        attempted_result_ids = {source.result_id for source in sources}

        semaphore = asyncio.Semaphore(max(1, config.EXTRACTION_MAX_CONCURRENT_CALLS))
        results = await asyncio.gather(
            *[self._extract_one_source_with_llm(job, header_by_result[source.result_id], source, semaphore) for source in sources]
        )
        evidence: list[EvidenceItem] = []
        failures: list[ExtractionFailure] = []
        blocked_fallback_result_ids: set[str] = set()
        for source_evidence, source_failures in results:
            evidence.extend(source_evidence)
            failures.extend(source_failures)
            for failure in source_failures:
                if failure.reason in {"llm quote could not be anchored", "source text failed quality filter"}:
                    blocked_fallback_result_ids.add(failure.result_id)
        if config.ENABLE_DEEP_SOURCE_REVIEW and len(evidence) < min(3, len(sources)):
            covered = {item.result_id for item in evidence}
            candidates = [source for source in sources if source.result_id not in covered] or sources[:1]
            deep_evidence = await self._extract_from_source_batch(job, header_by_result, candidates[:1], deep_review=True, start_index=len(evidence))
            evidence.extend(deep_evidence)
        return evidence, failures, blocked_fallback_result_ids, attempted_result_ids

    def _fallback_reason(
        self,
        result_id: str,
        llm_attempted_result_ids: set[str],
        llm_failure_reasons_by_result: dict[str, list[str]],
        *,
        has_llm_provider: bool,
        has_fetched_sources: bool,
    ) -> str:
        reasons = llm_failure_reasons_by_result.get(result_id, [])
        if reasons:
            return f"llm_returned_no_accepted_evidence: {'; '.join(reasons)}"
        if result_id in llm_attempted_result_ids:
            return "llm_returned_no_accepted_evidence: no accepted evidence item"
        if not has_llm_provider:
            return "llm_provider_unavailable"
        if not has_fetched_sources:
            return "llm_not_attempted_no_fetched_sources"
        return "llm_not_attempted_source_not_selected"

    async def _extract_one_source_with_llm(
        self,
        job: ResearchJob,
        header: SearchHeader,
        source: FetchedSource,
        semaphore: asyncio.Semaphore,
    ) -> tuple[list[EvidenceItem], list[ExtractionFailure]]:
        class ExtractedEvidence(BaseModel):
            claim: str
            source_quote: str
            relevance_to_query: float = 0.5
            target: str = ""
            dimension: str = ""
            evidence_fit_score: float = 0.0
            evidence_fit_notes: list[str] = Field(default_factory=list)
            limitations: list[str] = Field(default_factory=list)

        class ExtractionPayload(BaseModel):
            evidence_items: list[ExtractedEvidence] = Field(default_factory=list)

        cleaned = clean_source_text(source.text, url=source.url, title=source.title or header.title)
        if cleaned.failed_quality_filter:
            return [], [ExtractionFailure(result_id=source.result_id, reason="source text failed quality filter")]

        context = select_source_context(source.model_copy(update={"text": cleaned.text}), job, config.SOURCE_CONTEXT_TOKENS)
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract at most two atomic evidence items from this single source. "
                    "Every source_quote must be copied from the source context. "
                    "For each item, label the comparison target and decision dimension it directly supports. "
                    "Downscore tangential/domain-analogy evidence. "
                    "Return JSON only: {\"evidence_items\":[{\"claim\":\"...\",\"source_quote\":\"...\",\"relevance_to_query\":0.0,\"target\":\"...\",\"dimension\":\"...\",\"evidence_fit_score\":0.0,\"evidence_fit_notes\":[],\"limitations\":[]}]}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research objective: {job.objective}\nMust answer: {job.must_answer}\n"
                    f"Title: {source.title or header.title}\nURL: {source.url}\n"
                    f"Source context:\n{context}"
                ),
            },
        ]
        try:
            async with semaphore:
                response = await self.llm_provider.chat_json(
                    messages,
                    ExtractionPayload,
                    temperature=0,
                    max_tokens=config.EXTRACTION_MAX_TOKENS,
                    reasoning_effort=config.EXTRACTION_REASONING_EFFORT,
                )
            items = (response.parsed_json or {}).get("evidence_items", [])
        except Exception as exc:
            return [], [ExtractionFailure(result_id=source.result_id, reason=f"llm extraction failed: {exc.__class__.__name__}")]

        evidence = []
        failures = []
        for item in items[:2]:
            quote = str(item.get("source_quote", "")).strip()
            anchored = _anchor_quote(quote, cleaned.text)
            if not anchored:
                failures.append(ExtractionFailure(result_id=source.result_id, reason="llm quote could not be anchored"))
                continue
            anchored_quote, anchor_method, anchor_confidence = anchored
            limitations = list(item.get("limitations", []))
            limitations.extend([f"anchor_method:{anchor_method}", f"anchor_confidence:{anchor_confidence:.2f}"])
            evidence.append(
                self._with_evidence_fit(
                    job,
                    EvidenceItem(
                    evidence_id=f"ev_{job.job_id}_{len(evidence) + 1:03d}",
                    job_id=job.job_id,
                    result_id=source.result_id,
                    fetched_source_id=source.source_id,
                    claim=str(item.get("claim", "")).strip() or anchored_quote,
                    source_title=header.title,
                    source_url=header.url,
                    source_quote=anchored_quote,
                    quote_location="page",
                    source_type=source.source_type,
                    source_quality_score=source.source_quality_score,
                    extraction_method="llm_batch",
                    relevance_to_query=float(item.get("relevance_to_query", 0.5)),
                    target=str(item.get("target", "")).strip(),
                    dimension=str(item.get("dimension", "")).strip(),
                    evidence_fit_score=float(item.get("evidence_fit_score", 0.0) or 0.0),
                    evidence_fit_notes=list(item.get("evidence_fit_notes", [])),
                    limitations=limitations,
                    ),
                )
            )
        if not evidence and not failures:
            failures.append(ExtractionFailure(result_id=source.result_id, reason="llm extraction returned no evidence"))
        return evidence, failures

    async def _extract_from_source_batch(
        self,
        job: ResearchJob,
        header_by_result: dict[str, SearchHeader],
        sources: list[FetchedSource],
        deep_review: bool,
        start_index: int = 0,
    ) -> list[EvidenceItem]:
        class ExtractedEvidence(BaseModel):
            result_id: str
            claim: str
            source_quote: str
            relevance_to_query: float = 0.5
            target: str = ""
            dimension: str = ""
            evidence_fit_score: float = 0.0
            evidence_fit_notes: list[str] = Field(default_factory=list)
            limitations: list[str] = Field(default_factory=list)

        class ExtractionPayload(BaseModel):
            evidence_items: list[ExtractedEvidence] = Field(default_factory=list)

        source_blocks = []
        for source in sources:
            header = header_by_result[source.result_id]
            token_budget = config.SOURCE_DEEP_REVIEW_TOKENS if deep_review else config.SOURCE_CONTEXT_TOKENS
            context = (
                select_deep_review_context(source, job, token_budget)
                if deep_review
                else select_source_context(source, job, token_budget)
            )
            source_blocks.append(
                {
                    "result_id": source.result_id,
                    "title": source.title or header.title,
                    "url": source.url,
                    "source_type": source.source_type,
                    "context": context,
                }
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "Extract atomic quote-grounded evidence only from the supplied source contexts. "
                    "Every source_quote must be copied verbatim from that source context. "
                    "Include target, dimension, evidence_fit_score, and evidence_fit_notes for each item. Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research objective: {job.objective}\nMust answer: {job.must_answer}\n"
                    f"Deep review: {deep_review}\nSources:\n{source_blocks}"
                ),
            },
        ]
        try:
            response = await self.llm_provider.chat_json(messages, ExtractionPayload, temperature=0, max_tokens=4000 if deep_review else 2400)
            payload = response.parsed_json or {}
            items = payload.get("evidence_items", [])
        except Exception:
            return []

        source_by_result = {source.result_id: source for source in sources}
        evidence = []
        for item in items[: max(8, len(sources) * 2)]:
            result_id = str(item.get("result_id", "")).strip()
            source = source_by_result.get(result_id)
            header = header_by_result.get(result_id)
            quote = str(item.get("source_quote", "")).strip()
            anchored = _anchor_quote(quote, source.text) if source else None
            if not source or not header or not quote or not anchored:
                continue
            anchored_quote, anchor_method, anchor_confidence = anchored
            limitations = list(item.get("limitations", []))
            limitations.extend([f"anchor_method:{anchor_method}", f"anchor_confidence:{anchor_confidence:.2f}"])
            evidence.append(
                self._with_evidence_fit(
                    job,
                    EvidenceItem(
                    evidence_id=f"ev_{job.job_id}_{start_index + len(evidence) + 1:03d}",
                    job_id=job.job_id,
                    result_id=result_id,
                    fetched_source_id=source.source_id,
                    claim=str(item.get("claim", "")).strip() or quote,
                    source_title=header.title,
                    source_url=header.url,
                    source_quote=anchored_quote,
                    quote_location="page",
                    source_type=source.source_type,
                    source_quality_score=source.source_quality_score,
                    extraction_method="llm_deep_review" if deep_review else "llm_batch",
                    relevance_to_query=float(item.get("relevance_to_query", 0.5)),
                    target=str(item.get("target", "")).strip(),
                    dimension=str(item.get("dimension", "")).strip(),
                    evidence_fit_score=float(item.get("evidence_fit_score", 0.0) or 0.0),
                    evidence_fit_notes=list(item.get("evidence_fit_notes", [])),
                    limitations=limitations,
                    ),
                )
            )
        return evidence

    async def _extract_with_llm(self, job: ResearchJob, header: SearchHeader, fetched: FetchedSource) -> list[EvidenceItem]:
        class ExtractedEvidence(BaseModel):
            claim: str
            source_quote: str
            relevance_to_query: float = 0.5
            target: str = ""
            dimension: str = ""
            evidence_fit_score: float = 0.0
            evidence_fit_notes: list[str] = Field(default_factory=list)
            limitations: list[str] = Field(default_factory=list)

        class ExtractionPayload(BaseModel):
            evidence_items: list[ExtractedEvidence] = Field(default_factory=list)

        messages = [
            {"role": "system", "content": "Extract atomic quote-grounded evidence only from the provided source text."},
            {
                "role": "user",
                "content": (
                    f"Research objective: {job.objective}\nMust answer: {job.must_answer}\n"
                    f"Title: {header.title}\nURL: {header.url}\nSource text:\n{fetched.text[:6000]}"
                ),
            },
        ]
        try:
            response = await self.llm_provider.chat_json(messages, ExtractionPayload, temperature=0, max_tokens=1200)
            payload = response.parsed_json or {}
            items = payload.get("evidence_items", [])
        except Exception:
            return []
        evidence = []
        for item in items[:5]:
            quote = str(item.get("source_quote", "")).strip()
            if not quote or quote not in fetched.text:
                continue
            evidence.append(
                self._with_evidence_fit(
                    job,
                    EvidenceItem(
                    evidence_id=f"ev_{job.job_id}_{len(evidence) + 1:03d}",
                    job_id=job.job_id,
                    result_id=header.result_id,
                    fetched_source_id=fetched.source_id,
                    claim=str(item.get("claim", "")).strip() or quote,
                    source_title=header.title,
                    source_url=header.url,
                    source_quote=quote,
                    quote_location="page",
                    source_type=fetched.source_type,
                    source_quality_score=fetched.source_quality_score,
                    extraction_method="llm",
                    relevance_to_query=float(item.get("relevance_to_query", 0.5)),
                    target=str(item.get("target", "")).strip(),
                    dimension=str(item.get("dimension", "")).strip(),
                    evidence_fit_score=float(item.get("evidence_fit_score", 0.0) or 0.0),
                    evidence_fit_notes=list(item.get("evidence_fit_notes", [])),
                    limitations=list(item.get("limitations", [])),
                    ),
                )
            )
        return evidence

    def _with_evidence_fit(self, job: ResearchJob, item: EvidenceItem) -> EvidenceItem:
        planner = PlannerPrecontext(
            original_query=job.objective,
            query_interpretation=job.objective,
            precontext_claims=[],
            research_jobs=[job],
            coverage_checklist=job.must_answer,
        )
        planner.evidence_criteria = build_evidence_criteria(job.objective, planner)
        fit = score_evidence_fitness(planner, item)
        notes = [*item.evidence_fit_notes, *fit["notes"]]
        return item.model_copy(
            update={
                "target": item.target or fit["target"],
                "dimension": item.dimension or fit["dimension"],
                "evidence_fit_score": item.evidence_fit_score or fit["score"],
                "evidence_fit_notes": list(dict.fromkeys(notes))[:5],
            }
        )

    def _extract_quote(self, source_text: str | None, job: ResearchJob | None = None) -> str:
        if not source_text:
            return ""
        cleaned = " ".join(source_text.split())
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", cleaned)
            if len(s.strip().split()) >= 4 and not _looks_boilerplate_sentence(s)
        ]
        if job and sentences:
            job_terms = _terms(" ".join([job.objective, *job.search_queries, *job.must_answer]))
            return _cap_quote(max(sentences, key=lambda sentence: len(_terms(sentence) & job_terms)))
        for sentence in sentences:
            sentence = sentence.strip()
            return _cap_quote(sentence)
        return _cap_quote(cleaned) if len(cleaned.split()) >= 4 else ""

    def _relevance_score(self, job: ResearchJob, quote: str) -> float:
        quote_terms = _terms(quote)
        job_terms = _terms(" ".join([job.objective, *job.search_queries, *job.must_answer]))
        if not quote_terms or not job_terms:
            return 0.0
        overlap = len(quote_terms & job_terms)
        return min(1.0, round(overlap / max(1, min(len(job_terms), 10)), 2))


async def async_extract(job: ResearchJob, search_output: JobSearchOutput | list[SearchHeader]) -> JobEvidenceOutput:
    """Async compatibility entrypoint."""
    return await EvidenceExtractorAgent().extract(job, search_output)


def extract(job: ResearchJob, search_output: JobSearchOutput | list[SearchHeader]) -> JobEvidenceOutput:
    """Synchronous compatibility entrypoint for the current skeleton."""
    return asyncio.run(async_extract(job, search_output))


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(term) > 2}


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(text.split())


def _cap_quote(text: str, max_chars: int = 340) -> str:
    if len(text) <= max_chars:
        return text
    capped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return capped or text[:max_chars].strip()


def _anchor_quote(candidate_quote: str, source_text: str) -> tuple[str, str, float] | None:
    raw_quote = candidate_quote or ""
    quote = " ".join(raw_quote.split())
    source = " ".join((source_text or "").split())
    if not quote or not source:
        return None
    if raw_quote.strip() in source_text:
        return quote, "exact", 1.0

    normalized_quote = _normalize_anchor_text(quote)
    normalized_source = _normalize_anchor_text(source)
    if normalized_quote and normalized_quote in normalized_source:
        for sentence in _sentences(source):
            if _normalize_anchor_text(sentence) == normalized_quote:
                return sentence, "normalized", 1.0
        return quote, "normalized", 0.95

    quote_terms = _terms(quote)
    if not quote_terms:
        return None
    best_sentence = ""
    best_score = 0.0
    for sentence in _sentences(source):
        sentence_terms = _terms(sentence)
        if not sentence_terms:
            continue
        score = len(quote_terms & sentence_terms) / max(1, len(quote_terms))
        if score > best_score:
            best_sentence = sentence
            best_score = score
    if best_score >= 0.82:
        return _cap_quote(best_sentence), "fuzzy", best_score
    return None


def _normalize_anchor_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _looks_unusable_source_text(text: str) -> bool:
    sample = text.strip()[:1200].lower()
    if sample.startswith("%pdf"):
        return True
    binary_markers = ["/flatedecode", " endstream", " endobj", "\x00"]
    return sum(marker in sample for marker in binary_markers) >= 2


def _looks_boilerplate_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    markers = [
        "jump to content",
        "navigation menu",
        "toggle navigation",
        "sign in appearance",
        "contact sales get started",
        "skip to content",
        "skip to main content",
        "technology areas close",
        "products close",
        "solutions close",
        "resources close",
    ]
    return any(marker in lowered for marker in markers)
