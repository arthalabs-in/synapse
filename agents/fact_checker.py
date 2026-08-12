"""Fact checker: reconcile extracted evidence into a FactLedger."""

import asyncio
import re
from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel, Field

from config import config
from backend.models import (
    Contradiction,
    EvidenceItem,
    FactLedger,
    JobEvidenceOutput,
    JobSearchOutput,
    PlannerOutput,
    SearchHeader,
    VerifiedFact,
)
from backend.providers.llm.openai_compatible import EmptyVisibleContentError


class FactCheckerAgent:
    """Evidence reconciliation with optional LLM-assisted entailment."""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def check(
        self,
        original_query: str,
        planner_output: PlannerOutput,
        research_job_outputs: list[tuple[JobSearchOutput, JobEvidenceOutput]],
        search_headers: list[SearchHeader] | None = None,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> FactLedger:
        del planner_output
        headers = list(search_headers or [])
        evidence = list(evidence_items or [])

        for search_output, evidence_output in research_job_outputs:
            headers.extend(search_output.search_headers)
            evidence.extend(evidence_output.evidence_items)

        evidence = self._dedupe_evidence(evidence)
        valid_evidence, dropped = self._filter_valid_evidence(evidence)
        verified, partial, unsupported = await self._classify(valid_evidence, original_query)
        contradictions = self._find_contradictions(valid_evidence)

        return FactLedger(
            verified_facts=verified,
            partial_facts=partial,
            unsupported_claims=unsupported,
            contradictions=contradictions,
            dropped_evidence=dropped,
            source_quality_summary=dict(Counter(item.source_type for item in valid_evidence)),
            summary=(
                f"{len(verified)} verified, {len(partial)} partial, "
                f"{len(unsupported)} unsupported, {len(contradictions)} contradictions"
            ),
            )

    def _dedupe_evidence(self, evidence_items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
        deduped = []
        seen = set()
        for item in evidence_items:
            key = item.evidence_id or (item.result_id, item.source_quote)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _filter_valid_evidence(self, evidence_items: Iterable[EvidenceItem]) -> tuple[list[EvidenceItem], list[dict]]:
        valid = []
        dropped = []
        for item in evidence_items:
            if not item.source_url:
                dropped.append({"evidence_id": item.evidence_id, "reason": "missing source URL"})
                continue
            if not item.source_quote:
                dropped.append({"evidence_id": item.evidence_id, "reason": "missing source quote"})
                continue
            valid.append(item)
        return valid, dropped

    async def _classify(self, evidence_items: list[EvidenceItem], original_query: str) -> tuple[list[VerifiedFact], list[VerifiedFact], list[dict]]:
        verified = []
        partial = []
        unsupported = []
        llm_judgments = await self._llm_judge_batch(evidence_items, original_query) if self.llm_provider else {}

        for item in evidence_items:
            if _has_severe_quality_warning(item):
                unsupported.append(self._unsupported(item, "evidence failed quality gate"))
                continue
            judged = llm_judgments.get(item.evidence_id)
            if judged:
                status = judged["status"]
                fact = self._fact(
                    item,
                    status,
                    float(judged.get("confidence", 0.5)),
                    judged.get("explanation", ""),
                    verification_method="llm_batch",
                )
                if status == "VERIFIED":
                    verified.append(fact)
                elif status == "PARTIAL":
                    partial.append(fact)
                else:
                    unsupported.append(self._unsupported(item, judged.get("explanation", "unsupported by LLM")))
                continue
            support = self._support_score(item.claim, item.source_quote)
            threshold = config.FACT_CHECKER_SUPPORT_THRESHOLD
            if self._quote_contradicts_claim(item.claim, item.source_quote):
                unsupported.append(self._unsupported(item, "source quote conflicts with claim"))
            elif support >= threshold and item.extraction_method == "deterministic_fallback":
                partial.append(self._fact(item, "PARTIAL", 0.6, "Deterministic fallback evidence requires caveat"))
            elif support >= threshold and not item.limitations:
                verified.append(self._fact(item, "VERIFIED", 0.9, "Direct quote supports claim"))
            elif support >= max(0.35, threshold - 0.37):
                partial.append(self._fact(item, "PARTIAL", 0.55, "Partial support; caveat required"))
            else:
                unsupported.append(self._unsupported(item, "source quote does not support claim"))

        return verified, partial, unsupported

    def _unsupported(self, item: EvidenceItem, reason: str) -> dict[str, str]:
        return {
            "claim": item.claim,
            "evidence_id": item.evidence_id,
            "result_id": item.result_id,
            "reason": reason,
        }

    async def _llm_judge_batch(self, evidence_items: list[EvidenceItem], original_query: str) -> dict[str, dict]:
        if not evidence_items:
            return {}

        class EntailmentJudgment(BaseModel):
            evidence_id: str
            status: str
            confidence: float
            explanation: str
            quote_supports_claim: bool

        class EntailmentBatch(BaseModel):
            judgments: list[EntailmentJudgment] = Field(default_factory=list)

        payload = [
            {
                "evidence_id": item.evidence_id,
                "claim": item.claim,
                "source_quote": item.source_quote,
                "source_title": item.source_title,
                "source_url": item.source_url,
                "source_type": item.source_type,
            }
            for item in evidence_items
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Judge whether each source_quote supports its claim. "
                    "Return JSON with judgments. Status must be VERIFIED, PARTIAL, or UNSUPPORTED."
                ),
            },
            {"role": "user", "content": f"Original query: {original_query}\nEvidence items:\n{payload}"},
        ]
        try:
            response = await self.llm_provider.chat_json(messages, EntailmentBatch, temperature=0, max_tokens=3000)
            data = response.parsed_json or {}
        except EmptyVisibleContentError:
            # Phase 1.4: retry once with a bigger token budget and explicit thinking cap.
            if not config.FACT_CHECKER_LLM_RETRY_ON_EMPTY:
                return {}
            retry_kwargs: dict = {"temperature": 0, "max_tokens": 6000}
            try:
                response = await self.llm_provider.chat_json(messages, EntailmentBatch, **retry_kwargs)
                data = response.parsed_json or {}
            except Exception:
                return {}
        except Exception:
            return {}

        judgments = {}
        valid_ids = {item.evidence_id for item in evidence_items}
        for judgment in data.get("judgments", []):
            evidence_id = str(judgment.get("evidence_id", "")).strip()
            status = judgment.get("status")
            if evidence_id in valid_ids and status in {"VERIFIED", "PARTIAL", "UNSUPPORTED"}:
                judgments[evidence_id] = judgment
        return judgments

    async def _llm_judge(self, original_query: str, item: EvidenceItem) -> dict | None:
        class EntailmentJudgment(BaseModel):
            status: str
            confidence: float
            explanation: str
            quote_supports_claim: bool
            verification_method: str = "llm"

        messages = [
            {"role": "system", "content": "Judge whether the source quote supports the evidence claim. Return JSON only."},
            {
                "role": "user",
                "content": (
                    f"Original query: {original_query}\nClaim: {item.claim}\n"
                    f"Quote: {item.source_quote}\nTitle: {item.source_title}\nURL: {item.source_url}\n"
                    "Status must be VERIFIED, PARTIAL, or UNSUPPORTED."
                ),
            },
        ]
        try:
            response = await self.llm_provider.chat_json(messages, EntailmentJudgment, temperature=0, max_tokens=500)
            data = response.parsed_json or {}
            if data.get("status") not in {"VERIFIED", "PARTIAL", "UNSUPPORTED"}:
                return None
            return data
        except Exception:
            return None

    def _fact(self, item: EvidenceItem, status: str, confidence: float, notes: str, verification_method: str = "heuristic_fallback") -> VerifiedFact:
        return VerifiedFact(
            fact_id=f"fact_{item.evidence_id}",
            claim=item.claim,
            status=status,
            confidence=confidence,
            supporting_evidence_ids=[item.evidence_id],
            source_urls=[item.source_url],
            notes=notes,
            verification_method=verification_method,
        )

    def _find_contradictions(self, evidence_items: list[EvidenceItem]) -> list[Contradiction]:
        contradictions = []
        clean_items = [item for item in evidence_items if not _has_severe_quality_warning(item)]
        for index, left in enumerate(clean_items):
            for right in clean_items[index + 1 :]:
                if self._claims_conflict(left.claim, right.claim):
                    contradictions.append(
                        Contradiction(
                            cluster_id=f"contradiction_{len(contradictions) + 1:03d}",
                            topic=self._topic_label(left.claim, right.claim),
                            side_a_claim=left.claim,
                            side_a_evidence_ids=[left.evidence_id],
                            side_b_claim=right.claim,
                            side_b_evidence_ids=[right.evidence_id],
                            resolution="unresolved",
                        )
                    )
        return contradictions

    def _support_score(self, claim: str, quote: str) -> float:
        claim_terms = _important_terms(claim)
        quote_terms = _important_terms(quote)
        if not claim_terms or not quote_terms:
            return 0.0
        overlap = len(claim_terms & quote_terms)
        return overlap / len(claim_terms)

    def _quote_contradicts_claim(self, claim: str, quote: str) -> bool:
        return self._claims_conflict(claim, quote) and self._support_score(claim, quote) < config.FACT_CHECKER_SUPPORT_THRESHOLD

    def _claims_conflict(self, left: str, right: str) -> bool:
        left_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:gb|tb|%)?\b", left.lower()))
        right_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:gb|tb|%)?\b", right.lower()))
        shared_terms = _important_terms(left) & _important_terms(right)
        if left_numbers and right_numbers and left_numbers != right_numbers and len(shared_terms) >= 2:
            return True

        opposites = [("outperform", "underperform"), ("larger", "smaller"), ("increase", "decrease")]
        left_l = left.lower()
        right_l = right.lower()
        return any(a in left_l and b in right_l or b in left_l and a in right_l for a, b in opposites)

    def _topic_label(self, left: str, right: str) -> str:
        shared = sorted((_important_terms(left) & _important_terms(right)) - {"includes", "reports"})
        return " ".join(shared[:4]) or "conflicting evidence"


async def async_check(
    query: str,
    planner_output: PlannerOutput,
    job_outputs: list[tuple[JobSearchOutput, JobEvidenceOutput]],
) -> FactLedger:
    return await FactCheckerAgent().check(query, planner_output, job_outputs)


def check(
    query: str,
    planner_output: PlannerOutput,
    job_outputs: list[tuple[JobSearchOutput, JobEvidenceOutput]],
) -> FactLedger:
    return asyncio.run(async_check(query, planner_output, job_outputs))


def _important_terms(text: str) -> set[str]:
    stopwords = {
        "the",
        "that",
        "this",
        "with",
        "from",
        "into",
        "every",
        "most",
        "all",
        "and",
        "for",
        "has",
        "have",
        "had",
        "includes",
        "include",
        "included",
    }
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(term) > 2 and term not in stopwords
    }


def _has_severe_quality_warning(item: EvidenceItem) -> bool:
    severe = {"boilerplate_or_code", "support_page_navigation", "low_anchor_confidence", "code_like_quote"}
    limitations = set(item.limitations or [])
    if severe & limitations:
        return True
    limitation_text = " ".join(item.limitations or []).lower()
    severe_phrases = [
        "unrelated",
        "not directly address",
        "does not directly",
        "not directly answering",
        "specialized robotics",
        "specific to robotics",
        "not general agent",
        "does not mention gemini-specific",
        "not gemini-specific",
    ]
    return any(phrase in limitation_text for phrase in severe_phrases)
