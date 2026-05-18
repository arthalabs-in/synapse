"""Safe application of CoveragePatch operations to ResearchReport objects."""

from copy import deepcopy

from backend.models import (
    Contradiction,
    CoveragePatch,
    FactLedger,
    PatchApplicationResult,
    PatchOperation,
    ResearchReport,
    ReportSection,
    VerifiedFact,
)


class PatchApplicationError(ValueError):
    """Raised when a patch is unsafe or references unknown ledger items."""


def apply_patch(report: ResearchReport, patch: CoveragePatch, fact_ledger: FactLedger) -> PatchApplicationResult:
    """Apply validated patch operations and return before/after reports."""
    report_v1 = report.model_copy(deep=True)
    report_v2 = report.model_copy(deep=True)
    known_facts = _facts_by_id(fact_ledger)
    known_contradictions = {item.cluster_id: item for item in fact_ledger.contradictions}

    for operation in patch.patch_operations:
        _validate_operation(operation, known_facts, known_contradictions)
        _apply_operation(report_v2, operation, known_facts, known_contradictions)

    _recompute_confidence(report_v2, report_v1, patch)
    report_v2.report_id = "report_v2"
    report_v2.patch_applied = bool(patch.patch_operations)
    report_v2.used_fact_ids = _report_used_fact_ids(report_v2)
    report_v2.sources = sorted({url for section in report_v2.sections for url in section.citations})

    return PatchApplicationResult(
        report_v1=report_v1,
        report_v2=report_v2,
        applied_operations=patch.patch_operations,
    )


def _validate_operation(
    operation: PatchOperation,
    known_facts: dict[str, VerifiedFact],
    known_contradictions: dict[str, Contradiction],
) -> None:
    for fact_id in operation.fact_ids:
        if fact_id not in known_facts:
            raise PatchApplicationError(f"unknown fact_id: {fact_id}")
        fact = known_facts[fact_id]
        if operation.text and not _operation_text_is_supported(operation, fact):
            raise PatchApplicationError(f"patch text is not supported by fact_id: {fact_id}")

    for contradiction_id in operation.contradiction_ids:
        if contradiction_id not in known_contradictions:
            raise PatchApplicationError(f"unknown contradiction_id: {contradiction_id}")

    if not operation.fact_ids and not operation.contradiction_ids:
        raise PatchApplicationError("patch must reference valid fact_ids or contradiction_ids")


def _apply_operation(
    report: ResearchReport,
    operation: PatchOperation,
    known_facts: dict[str, VerifiedFact],
    known_contradictions: dict[str, Contradiction],
) -> None:
    fact_ids = operation.fact_ids or _fact_ids_for_contradictions(operation.contradiction_ids, known_facts, known_contradictions)
    if _apply_targeted_text_replacement(report, operation, fact_ids, known_facts):
        return
    if operation.op == "add":
        section = _find_or_create_section(report, operation.target_section_id or "sec_patch")
        _append_text(section, operation.text)
        _add_fact_refs(section, fact_ids, known_facts)
    elif operation.op == "replace":
        section = _find_required_section(report, operation.target_section_id)
        section.content = operation.text
        section.used_fact_ids = []
        section.citations = []
        _add_fact_refs(section, fact_ids, known_facts)
    elif operation.op == "weaken":
        section = _find_required_section(report, operation.target_section_id)
        section.content = operation.text
        _add_fact_refs(section, fact_ids, known_facts)
    elif operation.op == "add_caveat":
        section = _find_or_create_section(report, operation.target_section_id or "sec_caveats")
        _append_text(section, f"Caveat: {operation.text}")
        _add_fact_refs(section, fact_ids, known_facts)
    elif operation.op in {"remove", "remove_unsupported"}:
        _remove_unsupported_text(report, operation.text)
    else:
        raise PatchApplicationError(f"unsupported patch operation: {operation.op}")


def _apply_targeted_text_replacement(
    report: ResearchReport,
    operation: PatchOperation,
    fact_ids: list[str],
    known_facts: dict[str, VerifiedFact],
) -> bool:
    if not operation.original_text or operation.replacement_text is None:
        return False
    if operation.target_path == "answer_summary":
        if operation.original_text not in report.answer_summary:
            return False
        report.answer_summary = report.answer_summary.replace(operation.original_text, operation.replacement_text, 1)
        return True
    section = _find_required_section(report, operation.target_section_id)
    if operation.original_text not in section.content:
        return False
    section.content = section.content.replace(operation.original_text, operation.replacement_text, 1)
    _add_fact_refs(section, fact_ids, known_facts)
    return True


def _append_text(section: ReportSection, text: str) -> None:
    if not text:
        return
    section.content = f"{section.content.rstrip()}\n\n{text}".strip()


def _add_fact_refs(section: ReportSection, fact_ids: list[str], known_facts: dict[str, VerifiedFact]) -> None:
    for fact_id in fact_ids:
        fact = known_facts[fact_id]
        if fact_id not in section.used_fact_ids:
            section.used_fact_ids.append(fact_id)
        for url in fact.source_urls:
            if url not in section.citations:
                section.citations.append(url)


def _fact_ids_for_contradictions(
    contradiction_ids: list[str],
    known_facts: dict[str, VerifiedFact],
    known_contradictions: dict[str, Contradiction],
) -> list[str]:
    evidence_ids = set()
    for contradiction_id in contradiction_ids:
        contradiction = known_contradictions.get(contradiction_id)
        if not contradiction:
            continue
        evidence_ids.update(contradiction.side_a_evidence_ids)
        evidence_ids.update(contradiction.side_b_evidence_ids)

    fact_ids = []
    for fact_id, fact in known_facts.items():
        if evidence_ids & set(fact.supporting_evidence_ids):
            fact_ids.append(fact_id)
    return fact_ids


def _remove_unsupported_text(report: ResearchReport, text: str) -> None:
    target = text.removeprefix("Remove unsupported claim:").strip()
    if not target:
        return
    for section in report.sections:
        section.content = section.content.replace(target, "").strip()
    report.answer_summary = report.answer_summary.replace(target, "").strip()


def _find_required_section(report: ResearchReport, section_id: str | None) -> ReportSection:
    if not section_id:
        raise PatchApplicationError("target_section_id is required")
    section = _find_section(report, section_id)
    if not section:
        raise PatchApplicationError(f"unknown target_section_id: {section_id}")
    return section


def _find_or_create_section(report: ResearchReport, section_id: str) -> ReportSection:
    section = _find_section(report, section_id)
    if section:
        return section
    section = ReportSection(
        section_id=section_id,
        heading="Patch Updates",
        content="",
        used_fact_ids=[],
        citations=[],
    )
    report.sections.append(section)
    return section


def _find_section(report: ResearchReport, section_id: str) -> ReportSection | None:
    return next((section for section in report.sections if section.section_id == section_id), None)


def _facts_by_id(ledger: FactLedger) -> dict[str, VerifiedFact]:
    facts = {}
    for fact in [*ledger.verified_facts, *ledger.partial_facts]:
        facts[fact.fact_id] = fact
    return facts


def _operation_text_is_supported(operation: PatchOperation, fact: VerifiedFact) -> bool:
    if _text_is_supported(operation.text, fact):
        return True
    if operation.original_text and operation.replacement_text is not None:
        combined = f"{operation.original_text}\n{operation.replacement_text}"
        if fact.fact_id in combined:
            return True
    return False


def _text_is_supported(text: str, fact: VerifiedFact) -> bool:
    if not text.strip():
        return False
    if fact.claim in text or text in fact.claim:
        return True
    text_terms = _terms(text)
    fact_terms = _terms(fact.claim)
    if not text_terms or not fact_terms:
        return False
    return len(text_terms & fact_terms) / len(text_terms) >= 0.5


def _recompute_confidence(report_v2: ResearchReport, report_v1: ResearchReport, patch: CoveragePatch) -> None:
    report_v2.confidence_breakdown = deepcopy(report_v1.confidence_breakdown)
    old_coverage = report_v2.confidence_breakdown.get("coverage", 0.0)
    report_v2.confidence_breakdown["coverage"] = max(old_coverage, patch.coverage_score)
    if patch.patch_operations:
        report_v2.confidence_score = min(1.0, round(report_v1.confidence_score + 0.05 * len(patch.patch_operations), 2))
    else:
        report_v2.confidence_score = report_v1.confidence_score


def _report_used_fact_ids(report: ResearchReport) -> list[str]:
    seen = []
    for section in report.sections:
        for fact_id in section.used_fact_ids:
            if fact_id not in seen:
                seen.append(fact_id)
    return seen


def _terms(text: str) -> set[str]:
    return {term.lower().strip(".,:;()[]") for term in text.split() if len(term.strip(".,:;()[]")) > 2}
