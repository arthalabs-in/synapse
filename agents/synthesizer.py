"""Synthesizer agent: FactLedger -> cited ResearchReport."""

import asyncio
import re
from typing import Any

from pydantic import BaseModel, Field

from config import config
from agents.skill_loader import load_agent_skill
from backend.models import FactLedger, PlannerOutput, ResearchReport, ReportSection, VerifiedFact
from backend.providers.llm.openai_compatible import EmptyVisibleContentError


class ReportSectionPayload(BaseModel):
    heading: str
    content: str
    fact_ids: list[str] = Field(default_factory=list)


class KeyFindingPayload(BaseModel):
    finding: str
    fact_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ReportPayload(BaseModel):
    title: str
    answer_summary: str
    sections: list[ReportSectionPayload] = Field(default_factory=list)
    key_findings: list[KeyFindingPayload] = Field(default_factory=list)


class SynthesisDegradedError(RuntimeError):
    """Raised when live synthesis cannot produce a visible report."""


class SynthesizerAgent:
    """Writes reports using only verified and caveated partial facts."""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def synthesize(
        self,
        original_query: str,
        planner_output: PlannerOutput,
        job_summaries: list[dict[str, Any]],
        fact_ledger: FactLedger,
        coverage_matrix: dict[str, Any] | None = None,
    ) -> ResearchReport:
        verified = [fact for fact in fact_ledger.verified_facts if fact.status == "VERIFIED" and fact.source_urls]
        partial = [fact for fact in fact_ledger.partial_facts if fact.status == "PARTIAL" and fact.source_urls]
        breakdown = self._confidence_breakdown(verified, partial, fact_ledger, planner_output, job_summaries)
        confidence_score = self._weighted_confidence(breakdown)

        if self.llm_provider and (verified or partial):
            return await self._synthesize_with_llm(
                original_query=original_query,
                planner_output=planner_output,
                job_summaries=job_summaries,
                fact_ledger=fact_ledger,
                coverage_matrix=coverage_matrix or {},
                verified=verified,
                partial=partial,
                breakdown=breakdown,
                confidence_score=confidence_score,
            )

        sections = self._build_sections(verified, partial, fact_ledger)
        key_findings = [
            {
                "finding": fact.claim,
                "fact_ids": [fact.fact_id],
                "citations": fact.source_urls,
                "confidence": fact.confidence,
            }
            for fact in verified[:5]
        ]

        used_fact_ids = [fact_id for section in sections for fact_id in section.used_fact_ids]
        usable_fact_ids = {fact.fact_id for fact in verified + partial}

        return ResearchReport(
            title=original_query,
            answer_summary=self._summary(original_query, verified, partial),
            sections=sections,
            key_findings=key_findings,
            contradictions_or_uncertainties=[item.model_dump() for item in fact_ledger.contradictions],
            unsupported_not_included=fact_ledger.unsupported_claims,
            confidence_score=confidence_score,
            confidence_breakdown=breakdown,
            used_fact_ids=used_fact_ids,
            unused_fact_ids=sorted(usable_fact_ids - set(used_fact_ids)),
            sources=sorted({url for fact in verified + partial for url in fact.source_urls}),
        )

    async def _synthesize_with_llm(
        self,
        original_query: str,
        planner_output: PlannerOutput,
        job_summaries: list[dict[str, Any]],
        fact_ledger: FactLedger,
        coverage_matrix: dict[str, Any],
        verified: list[VerifiedFact],
        partial: list[VerifiedFact],
        breakdown: dict[str, float],
        confidence_score: float,
    ) -> ResearchReport:
        facts = verified + partial
        ranked_facts = sorted(facts, key=lambda fact: fact.confidence, reverse=True)[:8]
        quality_summary = (coverage_matrix or {}).get("summary", {})
        missing_count = len(quality_summary.get("missing_requirements", []) or [])
        weak_count = len(quality_summary.get("weak_requirements", []) or [])
        strong_count = len(quality_summary.get("strong_requirements", []) or [])
        fact_lines = "\n".join(
            f"- {fact.fact_id} ({fact.status}, confidence {fact.confidence:.2f}, notes={fact.notes or 'none'}): {fact.claim[:260]}"
            for fact in ranked_facts
        )
        limitation_lines = "\n".join(
            f"- missing: {item.get('target')} / {item.get('dimension')}"
            for item in quality_summary.get("missing_requirements", [])[:8]
        )
        weak_lines = "\n".join(
            f"- weak: {item.get('target')} / {item.get('dimension')} (score {item.get('score')})"
            for item in quality_summary.get("weak_requirements", [])[:8]
        )
        prompt = (
            "<question>\n"
            f"{original_query}\n"
            "</question>\n"
            "<coverage_matrix>\n"
            f"{coverage_matrix}\n"
            "</coverage_matrix>\n"
            "<coverage_limits>\n"
            f"strong_cells={strong_count}; weak_cells={weak_count}; missing_cells={missing_count}\n"
            f"{limitation_lines or 'none'}\n{weak_lines or ''}\n"
            "</coverage_limits>\n"
            "<facts>\n"
            f"{fact_lines}\n"
            "</facts>\n"
            "<instructions>\n"
            "Emit the final memo directly. Do not think step-by-step. Do not use markdown fences.\n"
            "Write a decision memo, not a fact dump. Use only facts listed above.\n"
            "Do not generalize a narrow source into a broad category claim.\n"
            "If a named option has weak or missing direct evidence, do not present it as fully evaluated.\n"
            "If many target/dimension cells are missing, avoid a definitive 'safest' winner and recommend the least-risk provisional path or say the evidence is insufficient.\n"
            "A winner is allowed only when its supporting facts cover the user's key dimensions better than each alternative.\n"
            "Every recommendation must explicitly name the major evidence gaps that could reverse it.\n"
            "Prefer a neutral comparison unless the evidence clearly supports a winner across coverage_matrix cells.\n"
            "Every SUMMARY sentence and every SECTION paragraph must include at least one FACT_ID in square brackets.\n"
            "Use this exact visible format:\n"
            "TITLE: <short title>\n"
            "SUMMARY: <2-3 sentence executive recommendation with [fact_id] citations>\n"
            "SECTION: <heading>\n"
            "<tight paragraph with [fact_id] citations>\n"
            "SECTION: <heading>\n"
            "<tight paragraph with [fact_id] citations>\n"
            "</instructions>"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise senior AI product strategist. Write a visible final answer only. "
                    "Never include hidden reasoning in the response."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        retry_messages = [
            {"role": "system", "content": "Return only visible final report text. No reasoning."},
            {
                "role": "user",
                "content": (
                    f"Question: {original_query}\nFacts:\n{fact_lines}\n\n"
                    "TITLE: Gemini Hackathon Agent Workflow\n"
                    "SUMMARY: Recommend the build in 2 sentences with [fact_id] citations.\n"
                    "SECTION: Recommendation\nWrite one paragraph with [fact_id] citations.\n"
                    "SECTION: Evidence\nWrite one paragraph with [fact_id] citations."
                ),
            },
        ]

        try:
            response = await self._call_synthesizer(messages, config.SYNTHESIZER_MAX_TOKENS)
            report = self._report_from_llm_text(
                original_query=original_query,
                text=response.text,
                facts=facts,
                fact_ledger=fact_ledger,
                breakdown=breakdown,
                confidence_score=confidence_score,
            )
            if report:
                return report
        except EmptyVisibleContentError:
            pass

        try:
            response = await self._call_synthesizer(retry_messages, config.SYNTHESIZER_MAX_TOKENS)
        except EmptyVisibleContentError as exc:
            raise SynthesisDegradedError(f"live synthesizer returned empty visible content after retry: {exc}") from exc
        report = self._report_from_llm_text(
            original_query=original_query,
            text=response.text,
            facts=facts,
            fact_ledger=fact_ledger,
            breakdown=breakdown,
            confidence_score=confidence_score,
        )
        if not report:
            raise SynthesisDegradedError("live synthesizer returned text that could not be parsed into a report")
        return report

    async def _call_synthesizer(self, messages: list[dict[str, str]], max_tokens: int):
        try:
            return await self.llm_provider.chat_text(
                messages,
                temperature=config.SYNTHESIZER_TEMPERATURE,
                max_tokens=max_tokens,
                reasoning_effort=config.SYNTHESIZER_REASONING_EFFORT,
                skills=[skill for skill in [load_agent_skill("research_synthesis")] if skill],
            )
        except EmptyVisibleContentError:
            raise
        except Exception as exc:
            raise SynthesisDegradedError(f"live synthesizer failed: {exc}") from exc

    def _report_from_llm_text(
        self,
        original_query: str,
        text: str,
        facts: list[VerifiedFact],
        fact_ledger: FactLedger,
        breakdown: dict[str, float],
        confidence_score: float,
    ) -> ResearchReport | None:
        cleaned = self._clean_llm_text(text)
        title = self._extract_labeled_block(cleaned, "TITLE", stop_labels={"SUMMARY", "SECTION"}) or original_query
        answer_summary = self._extract_labeled_block(cleaned, "SUMMARY", stop_labels={"SECTION"}) or self._first_paragraph(cleaned)
        if not answer_summary:
            return None

        fact_by_id = {fact.fact_id: fact for fact in facts}
        sections: list[ReportSection] = []
        parsed_sections = self._extract_sections(cleaned)
        if not parsed_sections:
            parsed_sections = [("Recommendation", cleaned)]

        for index, (heading, content) in enumerate(parsed_sections[:5], start=1):
            fact_ids = self._fact_ids_for_section(content, fact_by_id)
            if not content or not fact_ids:
                continue
            sections.append(
                ReportSection(
                    section_id=f"sec_llm_{index:02d}",
                    heading=heading,
                    content=content,
                    used_fact_ids=fact_ids,
                    citations=self._citations_for(fact_ids, fact_by_id),
                )
            )
        if not sections:
            return None

        key_findings = [
            {
                "finding": fact.claim,
                "fact_ids": [fact.fact_id],
                "citations": fact.source_urls,
                "confidence": fact.confidence,
            }
            for fact in facts[:5]
        ]

        used_fact_ids = [fact_id for section in sections for fact_id in section.used_fact_ids]
        usable_fact_ids = set(fact_by_id)
        return ResearchReport(
            title=title,
            answer_summary=answer_summary,
            sections=sections,
            key_findings=key_findings,
            contradictions_or_uncertainties=[item.model_dump() for item in fact_ledger.contradictions],
            unsupported_not_included=fact_ledger.unsupported_claims,
            confidence_score=confidence_score,
            confidence_breakdown=breakdown,
            used_fact_ids=used_fact_ids,
            unused_fact_ids=sorted(usable_fact_ids - set(used_fact_ids)),
            sources=sorted({url for fact in facts for url in fact.source_urls}),
        )

    def _clean_llm_text(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def _extract_labeled_block(self, text: str, label: str, stop_labels: set[str]) -> str:
        labels = "|".join(re.escape(stop) for stop in stop_labels)
        pattern = rf"(?ims)^\s*{re.escape(label)}\s*:\s*(.*?)(?=^\s*(?:{labels})\s*:|\Z)"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

    def _extract_sections(self, text: str) -> list[tuple[str, str]]:
        matches = list(re.finditer(r"(?im)^\s*SECTION\s*:\s*(.+?)\s*$", text))
        sections = []
        for index, match in enumerate(matches):
            heading = match.group(1).strip() or f"Finding {index + 1}"
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections.append((heading, content))
        return sections

    def _first_paragraph(self, text: str) -> str:
        without_labels = re.sub(r"(?im)^\s*(TITLE|SUMMARY|SECTION)\s*:.*$", "", text).strip()
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", without_labels) if part.strip()]
        if not paragraphs:
            return ""
        paragraph = paragraphs[0]
        return paragraph[:800].rsplit(" ", 1)[0].strip() if len(paragraph) > 800 else paragraph

    def _fact_ids_for_section(self, content: str, fact_by_id: dict[str, VerifiedFact]) -> list[str]:
        inline_ids = re.findall(r"\[([A-Za-z0-9_:-]+)\]", content)
        fact_ids = self._valid_fact_ids(inline_ids, fact_by_id)
        if fact_ids:
            return fact_ids
        top_fact = max(fact_by_id.values(), key=lambda fact: fact.confidence)
        return [top_fact.fact_id]

    def _valid_fact_ids(self, candidate_ids: list[Any], fact_by_id: dict[str, VerifiedFact]) -> list[str]:
        valid = []
        seen = set()
        for candidate in candidate_ids:
            fact_id = str(candidate).strip()
            if fact_id in fact_by_id and fact_id not in seen:
                seen.add(fact_id)
                valid.append(fact_id)
        return valid

    def _citations_for(self, fact_ids: list[str], fact_by_id: dict[str, VerifiedFact]) -> list[str]:
        return sorted({url for fact_id in fact_ids for url in fact_by_id[fact_id].source_urls})

    def _build_sections(
        self,
        verified: list[VerifiedFact],
        partial: list[VerifiedFact],
        ledger: FactLedger,
    ) -> list[ReportSection]:
        sections = []
        if verified:
            sections.append(
                ReportSection(
                    section_id="sec_verified",
                    heading="Verified Findings",
                    content="\n".join(f"- {fact.claim}" for fact in verified),
                    used_fact_ids=[fact.fact_id for fact in verified],
                    citations=sorted({url for fact in verified for url in fact.source_urls}),
                )
            )

        if partial:
            sections.append(
                ReportSection(
                    section_id="sec_partial",
                    heading="Caveated Findings",
                    content="\n".join(f"- Caveat: {fact.claim} ({fact.notes})" for fact in partial),
                    used_fact_ids=[fact.fact_id for fact in partial],
                    citations=sorted({url for fact in partial for url in fact.source_urls}),
                )
            )

        if ledger.contradictions:
            cited_fact_ids = [fact.fact_id for fact in verified + partial]
            cited_urls = sorted({url for fact in verified + partial for url in fact.source_urls})
            if cited_fact_ids and cited_urls:
                sections.append(
                    ReportSection(
                        section_id="sec_uncertainties",
                        heading="Contradictions And Uncertainties",
                        content="\n".join(
                            f"- Unresolved conflict: {item.side_a_claim} / {item.side_b_claim}"
                            for item in ledger.contradictions
                        ),
                        used_fact_ids=cited_fact_ids,
                        citations=cited_urls,
                    )
                )

        return sections

    def _summary(self, original_query: str, verified: list[VerifiedFact], partial: list[VerifiedFact]) -> str:
        if verified:
            return f"{original_query}: " + " ".join(fact.claim for fact in verified[:2])
        if partial:
            return f"{original_query}: only caveated findings are available."
        return f"{original_query}: no verified facts are available."

    def _confidence_breakdown(
        self,
        verified: list[VerifiedFact],
        partial: list[VerifiedFact],
        ledger: FactLedger,
        planner_output: PlannerOutput,
        job_summaries: list[dict[str, Any]],
    ) -> dict[str, float]:
        total_supported = len(verified) + len(partial) + len(ledger.unsupported_claims)
        verified_ratio = len(verified) / total_supported if total_supported else 0.0
        source_quality = self._source_quality_score(ledger)
        agreement = 1.0 if not ledger.contradictions else max(0.0, 1.0 - 0.25 * len(ledger.contradictions))
        recency = 0.5
        coverage = self._coverage_score(planner_output, job_summaries, verified, partial)
        return {
            "verified_ratio": round(verified_ratio, 2),
            "source_quality": round(source_quality, 2),
            "agreement": round(agreement, 2),
            "recency": round(recency, 2),
            "coverage": round(coverage, 2),
        }

    def _source_quality_score(self, ledger: FactLedger) -> float:
        counts = ledger.source_quality_summary
        if not counts:
            return 0.0
        total = sum(counts.values())
        weighted = sum(ledger.source_quality.get(source_type, 0) * count for source_type, count in counts.items())
        return min(1.0, weighted / max(1, total * 4))

    def _coverage_score(
        self,
        planner_output: PlannerOutput,
        job_summaries: list[dict[str, Any]],
        verified: list[VerifiedFact],
        partial: list[VerifiedFact],
    ) -> float:
        checklist_count = len(planner_output.coverage_checklist)
        fact_count = len(verified) + len(partial)
        if checklist_count:
            return min(1.0, fact_count / checklist_count)
        if job_summaries:
            return min(1.0, fact_count / max(1, len(job_summaries)))
        return 1.0 if fact_count else 0.0

    def _weighted_confidence(self, breakdown: dict[str, float]) -> float:
        score = (
            config.CONFIDENCE_VERIFIED_WEIGHT * breakdown["verified_ratio"]
            + config.CONFIDENCE_SOURCE_QUALITY_WEIGHT * breakdown["source_quality"]
            + config.CONFIDENCE_AGREEMENT_WEIGHT * breakdown["agreement"]
            + config.CONFIDENCE_RECENCY_WEIGHT * breakdown["recency"]
            + config.CONFIDENCE_COVERAGE_WEIGHT * breakdown["coverage"]
        )
        return max(0.0, min(1.0, round(score, 2)))


async def async_synthesize(
    query: str,
    fact_ledger: FactLedger,
    planner_output: PlannerOutput | None = None,
    job_summaries: list[dict[str, Any]] | None = None,
) -> ResearchReport:
    planner = planner_output or PlannerOutput(
        original_query=query,
        query_interpretation=query,
        precontext_claims=[],
        research_jobs=[],
    )
    return await SynthesizerAgent().synthesize(query, planner, job_summaries or [], fact_ledger)


def synthesize(query: str, fact_ledger: FactLedger) -> ResearchReport:
    """Synchronous compatibility entrypoint for the current skeleton."""
    return asyncio.run(async_synthesize(query, fact_ledger))
