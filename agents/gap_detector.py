"""Coverage auditor: compare report coverage against pipeline artifacts."""

import asyncio
import json
from typing import Any

from pydantic import BaseModel, Field

from agents.skill_loader import load_agent_skill
from backend.models import (
    CoverageDiff,
    CoveragePatch,
    EvidenceItem,
    FactLedger,
    JobEvidenceOutput,
    JobSearchOutput,
    PatchOperation,
    PlannerOutput,
    ResearchJob,
    ResearchReport,
    SearchHeader,
    VerifiedFact,
)


class RevisionBriefPayload(BaseModel):
    missing_intent: list[Any] = Field(default_factory=list)
    unused_supported_facts: list[Any] = Field(default_factory=list)
    option_balance_gaps: list[Any] = Field(default_factory=list)
    missed_contradictions_or_caveats: list[Any] = Field(default_factory=list)
    unsupported_slips: list[Any] = Field(default_factory=list)
    suggested_revision_focus: list[str] = Field(default_factory=list)
    patch_operations: list[Any] = Field(default_factory=list)


class CoverageAuditorAgent:
    """Finds coverage gaps and emits surgical patch operations."""

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def audit(
        self,
        original_query: str,
        planner_output: PlannerOutput,
        search_headers: list[SearchHeader],
        evidence_items: list[EvidenceItem],
        fact_ledger: FactLedger,
        report: ResearchReport,
        fetched_source_summary: dict[str, Any] | None = None,
        provider_metrics: dict[str, Any] | None = None,
        run_quality: dict[str, Any] | None = None,
    ) -> CoveragePatch:
        missed_verified = self._missed_verified_facts(fact_ledger, report)
        missed_caveats = self._missed_caveats(fact_ledger, report)
        missed_contradictions = self._missed_contradictions(fact_ledger, report)
        unused_search = self._unused_relevant_search_results(search_headers, evidence_items)
        missing_intent = self._missing_user_intent(planner_output, report)
        missing_intent.extend(self._coverage_matrix_gaps(run_quality or {}))
        unsupported_slips = self._unsupported_claims_in_report(fact_ledger, report)

        patch_operations = []
        if not _is_llm_authored_report(report):
            patch_operations.extend(self._patch_missing_verified(missed_verified))
            patch_operations.extend(self._patch_missing_caveats(missed_caveats))
            patch_operations.extend(self._patch_missing_contradictions(missed_contradictions))
        patch_operations.extend(self._patch_unsupported_slips(unsupported_slips))

        needs_new_search = bool(missing_intent and not patch_operations)
        followups = [self._followup_job(original_query, missing_intent)] if needs_new_search else []
        revision_brief = await self._revision_brief(
            original_query=original_query,
            planner_output=planner_output,
            search_headers=search_headers,
            evidence_items=evidence_items,
            fact_ledger=fact_ledger,
            report=report,
            fetched_source_summary=fetched_source_summary or {},
            provider_metrics=provider_metrics or {},
            run_quality=run_quality or {},
            deterministic_diff={
                "missed_verified_details": missed_verified,
                "missed_caveats": missed_caveats,
                "missed_contradictions": missed_contradictions,
                "search_result_unused_but_relevant": unused_search,
                "missing_user_intent": missing_intent,
                "unsupported_slips": unsupported_slips,
            },
        )
        if _is_llm_authored_report(report):
            patch_operations.extend(self._safe_revision_patch_operations(revision_brief, fact_ledger, report))

        total_checks = 5
        misses = sum(bool(item) for item in [missed_verified, missed_caveats, missed_contradictions, unused_search, missing_intent])
        coverage_score = max(0.0, min(1.0, round(1 - misses / total_checks, 2)))

        diff = CoverageDiff(
            missed_verified_details=missed_verified,
            missed_caveats=missed_caveats,
            missed_contradictions=missed_contradictions,
            search_result_unused_but_relevant=unused_search,
            missing_user_intent=missing_intent,
            revision_brief=revision_brief,
        )

        return CoveragePatch(
            coverage_score=coverage_score,
            coverage_diff=diff,
            missed_verified_details=missed_verified,
            missed_caveats=missed_caveats,
            missed_contradictions=missed_contradictions,
            search_results_unused_but_relevant=unused_search,
            missing_user_intent=missing_intent,
            revision_brief=revision_brief,
            patch_operations=patch_operations,
            needs_new_search=needs_new_search,
            followup_research_jobs=followups,
        )

    async def _revision_brief(
        self,
        *,
        original_query: str,
        planner_output: PlannerOutput,
        search_headers: list[SearchHeader],
        evidence_items: list[EvidenceItem],
        fact_ledger: FactLedger,
        report: ResearchReport,
        fetched_source_summary: dict[str, Any],
        provider_metrics: dict[str, Any],
        run_quality: dict[str, Any],
        deterministic_diff: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.llm_provider:
            return self._deterministic_revision_brief(deterministic_diff, fact_ledger, report)

        context = {
            "original_query": original_query,
            "coverage_checklist": planner_output.coverage_checklist,
            "research_jobs": [job.model_dump(mode="json") for job in planner_output.research_jobs],
            "search_headers": [_compact_model(header) for header in search_headers],
            "fetched_source_summary": fetched_source_summary,
            "evidence_items": [_compact_model(item) for item in evidence_items],
            "verified_facts": [fact.model_dump(mode="json") for fact in fact_ledger.verified_facts],
            "partial_facts": [fact.model_dump(mode="json") for fact in fact_ledger.partial_facts],
            "contradictions": [item.model_dump(mode="json") for item in fact_ledger.contradictions],
            "unsupported_claims": fact_ledger.unsupported_claims,
            "report_v1": report.model_dump(mode="json"),
            "provider_metrics": _compact_provider_metrics(provider_metrics),
            "run_quality": run_quality,
            "deterministic_diff": deterministic_diff,
        }
        messages = [
            {
                "role": "system",
                "content": "Return a compact JSON revision brief. Use only provided IDs and text.",
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False),
            },
        ]
        try:
            response = await self.llm_provider.chat_json(
                messages,
                RevisionBriefPayload,
                temperature=0,
                max_tokens=64000,
                reasoning_effort="high",
                skills=[skill for skill in [load_agent_skill("coverage-diff")] if skill],
            )
        except Exception as exc:
            brief = self._deterministic_revision_brief(deterministic_diff, fact_ledger, report)
            brief["diff_agent_error"] = exc.__class__.__name__
            return brief
        return response.parsed_json or {}

    def _deterministic_revision_brief(
        self,
        deterministic_diff: dict[str, Any],
        fact_ledger: FactLedger,
        report: ResearchReport,
    ) -> dict[str, Any]:
        used = set(report.used_fact_ids)
        for section in report.sections:
            used.update(section.used_fact_ids)
        unused_supported = [
            {"fact_id": fact.fact_id, "claim": fact.claim}
            for fact in [*fact_ledger.verified_facts, *fact_ledger.partial_facts]
            if fact.fact_id not in used
        ]
        focus = []
        if deterministic_diff.get("missing_user_intent"):
            focus.append("Address missing user-requested criteria.")
        if unused_supported:
            focus.append("Consider unused supported facts before final recommendation.")
        if deterministic_diff.get("missed_contradictions"):
            focus.append("Surface unresolved contradictions or caveats.")
        return {
            "missing_intent": deterministic_diff.get("missing_user_intent", []),
            "unused_supported_facts": unused_supported,
            "option_balance_gaps": [],
            "missed_contradictions_or_caveats": deterministic_diff.get("missed_contradictions", []) + deterministic_diff.get("missed_caveats", []),
            "unsupported_slips": deterministic_diff.get("unsupported_slips", []),
            "suggested_revision_focus": focus[:3],
            "patch_operations": [],
        }

    def _safe_revision_patch_operations(
        self,
        revision_brief: dict[str, Any],
        fact_ledger: FactLedger,
        report: ResearchReport,
    ) -> list[PatchOperation]:
        known_facts = {fact.fact_id: fact for fact in [*fact_ledger.verified_facts, *fact_ledger.partial_facts]}
        known_contradictions = {item.cluster_id: item for item in fact_ledger.contradictions}
        sections_by_id = {section.section_id: section for section in report.sections}
        operations = []

        for raw_operation in revision_brief.get("patch_operations") or []:
            raw_operation = _normalize_raw_patch_operation(raw_operation)
            try:
                operation = PatchOperation.model_validate(raw_operation)
            except Exception:
                continue
            operation = self._normalize_revision_patch_operation(operation)
            if not self._is_safe_revision_patch(operation, known_facts, known_contradictions, report, sections_by_id):
                continue
            operations.append(operation)
        return operations

    def _normalize_revision_patch_operation(self, operation: PatchOperation) -> PatchOperation:
        if operation.text.strip():
            return operation
        replacement_text = (operation.replacement_text or "").strip()
        if replacement_text:
            return operation.model_copy(update={"text": replacement_text})
        original_text = (operation.original_text or "").strip()
        if operation.op in {"remove", "remove_unsupported"} and original_text:
            return operation.model_copy(update={"text": original_text})
        return operation

    def _is_safe_revision_patch(
        self,
        operation: PatchOperation,
        known_facts: dict[str, VerifiedFact],
        known_contradictions: dict[str, Any],
        report: ResearchReport,
        sections_by_id: dict[str, Any],
    ) -> bool:
        if operation.op in {"replace", "weaken"} and operation.target_section_id not in sections_by_id:
            return False
        if operation.fact_ids:
            if any(fact_id not in known_facts for fact_id in operation.fact_ids):
                return False
            return any(_operation_is_supported_by_fact(operation, known_facts[fact_id]) for fact_id in operation.fact_ids)
        if operation.contradiction_ids:
            return all(contradiction_id in known_contradictions for contradiction_id in operation.contradiction_ids)
        return False

    def _missed_verified_facts(self, ledger: FactLedger, report: ResearchReport) -> list[dict[str, str]]:
        used = set(report.used_fact_ids)
        for section in report.sections:
            used.update(section.used_fact_ids)
        return [
            {"fact_id": fact.fact_id, "claim": fact.claim}
            for fact in ledger.verified_facts
            if fact.fact_id not in used
        ]

    def _missed_caveats(self, ledger: FactLedger, report: ResearchReport) -> list[dict[str, str]]:
        report_text = self._report_text(report).lower()
        missed = []
        for fact in ledger.partial_facts:
            if fact.fact_id in report.used_fact_ids and "caveat" not in report_text and "partial" not in report_text:
                missed.append({"fact_id": fact.fact_id, "claim": fact.claim, "notes": fact.notes})
            elif fact.claim in report_text and "caveat" not in report_text and "partial" not in report_text:
                missed.append({"fact_id": fact.fact_id, "claim": fact.claim, "notes": fact.notes})
        return missed

    def _missed_contradictions(self, ledger: FactLedger, report: ResearchReport) -> list[dict[str, str]]:
        report_text = self._report_text(report).lower()
        missed = []
        for contradiction in ledger.contradictions:
            mentioned = (
                contradiction.cluster_id in report_text
                or contradiction.topic.lower() in report_text and "conflict" in report_text
                or contradiction.topic.lower() in report_text and "uncertain" in report_text
            )
            if not mentioned:
                missed.append(
                    {
                        "contradiction_id": contradiction.cluster_id,
                        "topic": contradiction.topic,
                        "side_a_claim": contradiction.side_a_claim,
                        "side_b_claim": contradiction.side_b_claim,
                    }
                )
        return missed

    def _unused_relevant_search_results(
        self,
        search_headers: list[SearchHeader],
        evidence_items: list[EvidenceItem],
    ) -> list[dict[str, str]]:
        used_result_ids = {item.result_id for item in evidence_items}
        relevant_types = {"official", "paper", "docs"}
        return [
            {
                "result_id": header.result_id,
                "title": header.title,
                "url": header.url,
                "source_type_guess": header.source_type_guess,
            }
            for header in search_headers
            if header.result_id not in used_result_ids and header.source_type_guess in relevant_types
        ]

    def _missing_user_intent(self, planner_output: PlannerOutput, report: ResearchReport) -> list[dict[str, str]]:
        report_text = self._report_text(report).lower()
        missing = []
        for item in planner_output.coverage_checklist:
            if item.lower() not in report_text:
                missing.append({"intent": item, "reason": "coverage checklist item not addressed"})
        return missing

    def _coverage_matrix_gaps(self, run_quality: dict[str, Any]) -> list[dict[str, str]]:
        summary = run_quality.get("evidence_quality_summary") or {}
        gaps = []
        for item in summary.get("missing_requirements", [])[:8]:
            gaps.append(
                {
                    "intent": f"{item.get('target', 'option')} / {item.get('dimension', 'dimension')}",
                    "reason": "coverage matrix has no quote-grounded evidence for this target and dimension",
                }
            )
        for item in summary.get("weak_requirements", [])[:6]:
            gaps.append(
                {
                    "intent": f"{item.get('target', 'option')} / {item.get('dimension', 'dimension')}",
                    "reason": "coverage matrix marks this target and dimension as weakly supported",
                }
            )
        return gaps

    def _unsupported_claims_in_report(self, ledger: FactLedger, report: ResearchReport) -> list[dict[str, str]]:
        report_text = self._report_text(report).lower()
        slips = []
        for item in ledger.unsupported_claims:
            claim = str(item.get("claim", ""))
            if claim and claim.lower() in report_text:
                slips.append(
                    {
                        "claim": claim,
                        "evidence_id": str(item.get("evidence_id", "")),
                        "result_id": str(item.get("result_id", "")),
                    }
                )
        return slips

    def _patch_missing_verified(self, missed: list[dict[str, str]]) -> list[PatchOperation]:
        return [
            PatchOperation(
                op="add",
                target_section_id="sec_verified",
                text=f"Add verified detail: {item['claim']}",
                fact_ids=[item["fact_id"]],
                reason="Verified fact missing from report",
            )
            for item in missed
            if item.get("fact_id") and _patchable_claim(item.get("claim", ""))
        ]

    def _patch_missing_caveats(self, missed: list[dict[str, str]]) -> list[PatchOperation]:
        return [
            PatchOperation(
                op="add_caveat",
                target_section_id="sec_partial",
                text=f"Caveat required: {item['claim']}",
                fact_ids=[item["fact_id"]],
                reason="Partial fact stated without explicit caveat",
            )
            for item in missed
            if item.get("fact_id")
        ]

    def _patch_missing_contradictions(self, missed: list[dict[str, str]]) -> list[PatchOperation]:
        return [
            PatchOperation(
                op="add_caveat",
                target_section_id="sec_uncertainties",
                text=f"Add unresolved contradiction: {item['side_a_claim']} / {item['side_b_claim']}",
                contradiction_ids=[item["contradiction_id"]],
                reason="Contradiction omitted from report",
            )
            for item in missed
            if item.get("contradiction_id")
            and _patchable_claim(item.get("side_a_claim", ""))
            and _patchable_claim(item.get("side_b_claim", ""))
        ]

    def _patch_unsupported_slips(self, slips: list[dict[str, str]]) -> list[PatchOperation]:
        return [
            PatchOperation(
                op="remove",
                target_section_id=None,
                text=f"Remove unsupported claim: {item['claim']}",
                result_ids=[item["result_id"]],
                reason="Unsupported claim appears in report",
            )
            for item in slips
            if item.get("result_id")
        ]

    def _followup_job(self, original_query: str, missing_intent: list[dict[str, str]]) -> ResearchJob:
        intent = missing_intent[0]["intent"]
        return ResearchJob(
            job_id="job_followup_001",
            job_name="Follow-up Coverage Search",
            objective=f"Find evidence for missing coverage area: {intent}",
            search_queries=[f"{original_query} {intent}"],
            source_priorities=["official", "paper", "docs"],
            must_answer=[intent],
        )

    def _report_text(self, report: ResearchReport) -> str:
        return " ".join(
            [
                report.title,
                report.answer_summary,
                *[section.content for section in report.sections],
                *[finding.finding for finding in report.key_findings],
            ]
        )


def _patchable_claim(claim: str) -> bool:
    lowered = claim.lower()
    noisy_markers = [
        "x-goog-api-key",
        "curl ",
        " -h ",
        " -x post",
        "content-type: application/json",
        "send feedback",
        "home gemini api docs",
        "skip to main content",
        "qualifications for tiers",
        "cumulative spending",
    ]
    if any(marker in lowered for marker in noisy_markers):
        return False
    if claim.count("\\") >= 2 or claim.count("{") >= 2:
        return False
    return len(claim.split()) >= 3


def _operation_is_supported_by_fact(operation: PatchOperation, fact: VerifiedFact) -> bool:
    if _text_is_supported_by_fact(operation.text, fact):
        return True
    if operation.original_text and operation.replacement_text is not None:
        combined = f"{operation.original_text}\n{operation.replacement_text}"
        if fact.fact_id in combined:
            return True
    return False


def _text_is_supported_by_fact(text: str, fact: VerifiedFact) -> bool:
    if not text.strip():
        return False
    if fact.claim in text or text in fact.claim:
        return True
    text_terms = _terms(text)
    fact_terms = _terms(fact.claim)
    if not text_terms or not fact_terms:
        return False
    return len(text_terms & fact_terms) / len(text_terms) >= 0.5


def _normalize_raw_patch_operation(raw_operation: Any) -> Any:
    if not isinstance(raw_operation, dict) or raw_operation.get("text"):
        return raw_operation
    replacement_text = str(raw_operation.get("replacement_text") or "").strip()
    original_text = str(raw_operation.get("original_text") or "").strip()
    if replacement_text:
        return {**raw_operation, "text": replacement_text}
    if raw_operation.get("op") in {"remove", "remove_unsupported"} and original_text:
        return {**raw_operation, "text": original_text}
    return raw_operation


def _terms(text: str) -> set[str]:
    return {term.lower().strip(".,:;()[]") for term in text.split() if len(term.strip(".,:;()[]")) > 2}


def _compact_model(item: Any) -> dict[str, Any]:
    data = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
    compact = {}
    for key, value in data.items():
        if key in {"text", "raw_response"}:
            continue
        if isinstance(value, str) and len(value) > 800:
            compact[key] = value[:800]
        else:
            compact[key] = value
    return compact


def _compact_provider_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    if not metrics:
        return {}
    return {
        "llm_provider": metrics.get("llm_provider"),
        "synthesizer_llm_provider": metrics.get("synthesizer_llm_provider"),
        "llm_call_count": metrics.get("llm_call_count"),
        "truncated_by_reasoning_count": metrics.get("truncated_by_reasoning_count"),
        "source_fetch": metrics.get("source_fetch"),
        "run_quality": metrics.get("run_quality"),
    }


def _is_llm_authored_report(report: ResearchReport) -> bool:
    return any(section.section_id.startswith("sec_llm_") for section in report.sections)


async def async_audit(
    query: str,
    planner_output: PlannerOutput,
    job_outputs: list[tuple[JobSearchOutput, JobEvidenceOutput]],
    fact_ledger: FactLedger,
    report: ResearchReport,
) -> CoveragePatch:
    search_headers = []
    evidence_items = []
    for search_output, evidence_output in job_outputs:
        search_headers.extend(search_output.search_headers)
        evidence_items.extend(evidence_output.evidence_items)
    return await CoverageAuditorAgent().audit(query, planner_output, search_headers, evidence_items, fact_ledger, report)


def audit(
    query: str,
    planner_output: PlannerOutput,
    job_outputs: list[tuple[JobSearchOutput, JobEvidenceOutput]],
    fact_ledger: FactLedger,
    report: ResearchReport,
) -> CoveragePatch:
    return asyncio.run(async_audit(query, planner_output, job_outputs, fact_ledger, report))
