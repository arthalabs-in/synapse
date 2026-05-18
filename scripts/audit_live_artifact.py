"""Build a causal quality audit for a SYNAPSE live artifact."""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


NOISY_MARKERS = [
    "x-goog-api-key",
    "curl ",
    "content-type: application/json",
    "send feedback",
    "skip to main content",
    "home gemini api docs",
    "cumulative spending",
    "qualifications for tiers",
    "navigation",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    parser.add_argument("--out", default="docs/LIVE_GOLDEN_CAUSAL_AUDIT.md")
    args = parser.parse_args()

    payload = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    report = build_audit(payload)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def build_audit(payload: dict[str, Any]) -> str:
    headers = payload.get("search_headers", [])
    fetched = payload.get("fetched_sources", [])
    evidence = payload.get("evidence_items", [])
    ledger = payload.get("fact_ledger") or {}
    report = payload.get("report") or payload.get("report_v2") or {}

    headers_by_result = {item.get("result_id"): item for item in headers}
    fetched_by_result = {item.get("result_id"): item for item in fetched}
    evidence_by_id = {item.get("evidence_id"): item for item in evidence}
    facts = (ledger.get("verified_facts") or []) + (ledger.get("partial_facts") or [])
    facts_by_id = {fact.get("fact_id"): fact for fact in facts}
    report_fact_ids = _report_fact_ids(report)

    lines = [
        "# Live Golden Causal Audit",
        "",
        "## Executive Read",
        f"- Query: {payload.get('research_question', '')}",
        f"- Degraded: {payload.get('degraded')} | Errors: {len(payload.get('errors') or [])}",
        f"- Validator-critical counts: {len(headers)} headers, {len(fetched)} fetched sources, {len(evidence)} evidence items, {len(facts)} supported facts.",
        f"- Report sections: {len(report.get('sections') or [])}; LLM-authored sections: {sum(1 for s in report.get('sections', []) if str(s.get('section_id', '')).startswith('sec_llm_'))}.",
        f"- Patch operations: {len((payload.get('coverage_patch') or {}).get('patch_operations') or [])}.",
        "",
        "## Stage Timing And LLM Calls",
    ]
    for name, seconds in (payload.get("timings") or {}).items():
        lines.append(f"- {name}: {seconds}s")

    metrics = payload.get("provider_metrics") or {}
    lines.append("")
    lines.append("### LLM Calls")
    for call in metrics.get("llm_calls") or []:
        label = call.get("schema") or "chat_text"
        status = "ok" if call.get("ok") else f"fail:{call.get('error_type')}"
        lines.append(
            "- "
            f"#{call.get('call_index')} {label}: {status}, finish={call.get('finish_reason')}, "
            f"visible={call.get('visible_chars')}, reasoning={call.get('reasoning_tokens')}, "
            f"max={call.get('max_tokens')}, truncated_by_reasoning={call.get('truncated_by_reasoning')}"
        )

    run_quality = payload.get("run_quality") or ((payload.get("provider_metrics") or {}).get("run_quality") or {})
    if run_quality:
        signals = run_quality.get("signals") or {}
        lines.extend(
            [
                "",
                "## Run Quality",
                f"- Grade: {run_quality.get('grade')} ({run_quality.get('score')})",
                f"- Evidence mix: total={signals.get('evidence_count')} llm={signals.get('llm_evidence_count')} fallback={signals.get('fallback_evidence_count')} snippets={signals.get('snippet_evidence_count')}",
                f"- Source health: fetched={signals.get('successful_fetched_source_count')}/{signals.get('fetched_source_count')} avg_quality={signals.get('average_source_quality')}",
                f"- Ledger health: verified={signals.get('verified_fact_count')} partial={signals.get('partial_fact_count')} unsupported={signals.get('unsupported_claim_count')} contradictions={signals.get('contradiction_count')}",
                f"- Fallback reasons: {run_quality.get('fallback_reasons') or {}}",
            ]
        )

    lines.extend(["", "## Source Cleaning And Extraction Health"])
    fetched_with_metadata = [source for source in fetched if source.get("metadata")]
    if fetched_with_metadata:
        total_raw = sum(int((source.get("metadata") or {}).get("raw_text_chars") or len(source.get("text") or "")) for source in fetched)
        total_clean = sum(int((source.get("metadata") or {}).get("clean_text_chars") or len(source.get("text") or "")) for source in fetched)
        markers = defaultdict(int)
        for source in fetched:
            for marker in (source.get("metadata") or {}).get("removed_noise_markers") or []:
                markers[marker] += 1
        lines.append(f"- Raw text chars: {total_raw}")
        lines.append(f"- Clean text chars: {total_clean}")
        lines.append(f"- Cleaning ratio: {round(total_clean / total_raw, 2) if total_raw else 0}")
        lines.append(f"- Removed marker counts: {dict(sorted(markers.items()))}")
    by_method = defaultdict(int)
    for item in evidence:
        by_method[item.get("extraction_method") or "unknown"] += 1
    failure_reasons = defaultdict(int)
    for summary in payload.get("job_summaries") or []:
        failure_reasons["job_extraction_failures"] += int(summary.get("extraction_failure_count") or 0)
    lines.append(f"- Evidence by extraction method: {dict(sorted(by_method.items()))}")
    fallback_reasons = defaultdict(int)
    for item in evidence:
        if item.get("extraction_method") == "deterministic_fallback":
            fallback_reasons[item.get("fallback_reason") or "unspecified"] += 1
    lines.append(f"- Fallback reason summary: {dict(sorted(fallback_reasons.items()))}")
    lines.append(f"- Extraction failure summary: {dict(sorted(failure_reasons.items()))}")

    lines.extend(["", "## Planner Output"])
    planner = payload.get("planner_precontext") or {}
    lines.append(f"- Interpretation: {planner.get('query_interpretation', '')}")
    lines.append(f"- Planning risks: {planner.get('planning_risks') or []}")
    lines.append("- Coverage checklist:")
    for item in planner.get("coverage_checklist") or []:
        lines.append(f"  - {item}")
    lines.append("- Research jobs:")
    for job in planner.get("research_jobs") or []:
        lines.append(f"  - {job.get('job_id')}: {job.get('job_name')} | objective={job.get('objective')}")
        for query in job.get("search_queries") or []:
            lines.append(f"    - query: {query}")

    lines.extend(["", "## Job Causal Chains"])
    for job in planner.get("research_jobs") or []:
        job_id = job.get("job_id")
        job_headers = [item for item in headers if item.get("job_id") == job_id]
        job_evidence = [item for item in evidence if item.get("job_id") == job_id]
        lines.append(f"### {job_id}: {job.get('job_name')}")
        lines.append(f"- Headers selected: {len(job_headers)}")
        lines.append(f"- Evidence extracted: {len(job_evidence)}")
        for item in job_headers:
            result_id = item.get("result_id")
            source = fetched_by_result.get(result_id, {})
            source_evidence = [ev for ev in job_evidence if ev.get("result_id") == result_id]
            lines.append(
                f"- `{result_id}` {item.get('title')} | {item.get('url')} | "
                f"fetch={source.get('fetch_status')} success={source.get('success')} text_chars={len(source.get('text') or '')}"
            )
            for ev in source_evidence:
                warning = _quality_warning(ev.get("source_quote", ""))
                suffix = f" | warning={warning}" if warning else ""
                fallback = f" fallback_reason={ev.get('fallback_reason')}" if ev.get("fallback_reason") else ""
                lines.append(
                    f"  - evidence `{ev.get('evidence_id')}` method={ev.get('extraction_method')} "
                    f"quality={ev.get('source_quality_score')}{fallback} quote={_short(ev.get('source_quote', ''))}{suffix}"
                )

    lines.extend(["", "## Fact Ledger Trace"])
    for fact in facts:
        evidence_ids = fact.get("supporting_evidence_ids") or []
        used = fact.get("fact_id") in report_fact_ids
        warnings = []
        for evidence_id in evidence_ids:
            ev = evidence_by_id.get(evidence_id, {})
            warning = _quality_warning(ev.get("source_quote", ""))
            if warning:
                warnings.append(warning)
        lines.append(
            f"- `{fact.get('fact_id')}` status={fact.get('status')} used_in_report={used} "
            f"confidence={fact.get('confidence')} evidence={evidence_ids}"
        )
        lines.append(f"  - claim: {_short(fact.get('claim', ''), 260)}")
        lines.append(f"  - urls: {', '.join(fact.get('source_urls') or [])}")
        if warnings:
            lines.append(f"  - quality warnings: {sorted(set(warnings))}")

    lines.extend(["", "## Report Citation Trace"])
    lines.append(f"- Title: {report.get('title', '')}")
    lines.append(f"- Summary: {_short(report.get('answer_summary', ''), 500)}")
    for section in report.get("sections") or []:
        fact_ids = section.get("used_fact_ids") or []
        missing = [fact_id for fact_id in fact_ids if fact_id not in facts_by_id]
        lines.append(
            f"### {section.get('section_id')}: {section.get('heading')}"
        )
        lines.append(f"- fact_ids: {fact_ids}")
        lines.append(f"- citations: {len(section.get('citations') or [])}")
        if missing:
            lines.append(f"- missing fact IDs: {missing}")
        lines.append(f"- content: {_short(section.get('content', ''), 700)}")

    lines.extend(["", "## Weak Points"])
    weak_points = _weak_points(payload, facts, evidence, report)
    if weak_points:
        for item in weak_points:
            lines.append(f"- {item}")
    else:
        lines.append("- No major structural weak points detected.")

    revision_brief = (payload.get("coverage_patch") or {}).get("revision_brief") or {}
    if revision_brief:
        lines.extend(["", "## Revision Brief"])
        for key in [
            "missing_intent",
            "unused_supported_facts",
            "option_balance_gaps",
            "missed_contradictions_or_caveats",
            "unsupported_slips",
            "suggested_revision_focus",
        ]:
            value = revision_brief.get(key)
            if value:
                lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")

    patch_operations = (payload.get("coverage_patch") or {}).get("patch_operations") or []
    if patch_operations:
        lines.extend(["", "## UI-Ready Patch Operations"])
        for op in patch_operations:
            refs = op.get("fact_ids") or op.get("contradiction_ids") or op.get("result_ids") or []
            lines.append(
                f"- `{op.get('edit_id') or op.get('op')}` {op.get('op')} | "
                f"label={op.get('edit_label') or ''} | location={op.get('target_path') or op.get('target_section_id') or 'report'} | refs={refs}"
            )
            lines.append(f"  - reason: {_short(op.get('reason', ''), 260)}")
            if op.get("original_text") or op.get("replacement_text"):
                lines.append(f"  - before: {_short(op.get('original_text', ''), 260)}")
                lines.append(f"  - after: {_short(op.get('replacement_text') or op.get('text') or '', 260)}")

    lines.extend(["", "## Recommended Next Fixes"])
    lines.extend(_recommended_fixes(payload, facts, evidence, report))
    lines.append("")
    return "\n".join(lines)


def _report_fact_ids(report: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for section in report.get("sections") or []:
        ids.update(section.get("used_fact_ids") or [])
    for finding in report.get("key_findings") or []:
        ids.update(finding.get("fact_ids") or [])
    return ids


def _quality_warning(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in NOISY_MARKERS):
        return "boilerplate_or_code"
    if len(text.split()) > 45:
        return "long_quote"
    if re.search(r"\b[A-Z_]{4,}\b", text) and ("{" in text or "\\" in text):
        return "code_like_quote"
    return ""


def _weak_points(payload: dict[str, Any], facts: list[dict[str, Any]], evidence: list[dict[str, Any]], report: dict[str, Any]) -> list[str]:
    items = []
    if any((call.get("truncated_by_reasoning") for call in (payload.get("provider_metrics") or {}).get("llm_calls") or [])):
        items.append("Some upstream LLM calls still truncate on hidden reasoning; synthesis is fixed with 64K, extraction is not.")
    if evidence and all(item.get("extraction_method") == "deterministic_fallback" for item in evidence):
        items.append("All evidence came from deterministic fallback; LLM extraction is not yet reliably contributing accepted evidence.")
    noisy_evidence = [item.get("evidence_id") for item in evidence if _quality_warning(item.get("source_quote", ""))]
    if noisy_evidence:
        items.append(f"Noisy evidence quotes remain: {noisy_evidence}.")
    report_ids = _report_fact_ids(report)
    unused = [fact.get("fact_id") for fact in facts if fact.get("fact_id") not in report_ids]
    if unused:
        items.append(f"Supported facts unused by the final report: {unused}.")
    contradictions = (payload.get("fact_ledger") or {}).get("contradictions") or []
    if contradictions:
        items.append(f"Fact checker produced {len(contradictions)} contradictions; inspect whether these are real conflicts or quote-noise artifacts.")
    return items


def _recommended_fixes(payload: dict[str, Any], facts: list[dict[str, Any]], evidence: list[dict[str, Any]], report: dict[str, Any]) -> list[str]:
    fixes = []
    if any((call.get("schema") == "ExtractionPayload" and call.get("truncated_by_reasoning") for call in (payload.get("provider_metrics") or {}).get("llm_calls") or [])):
        fixes.append("- Give extraction either a larger per-stage max token budget or a non-reasoning model; currently extraction can die before visible JSON.")
    if all(item.get("extraction_method") == "deterministic_fallback" for item in evidence):
        fixes.append("- Add fuzzy quote anchoring for LLM extraction so useful model-selected quotes are accepted when whitespace differs from fetched text.")
    if any(_quality_warning(item.get("source_quote", "")) for item in evidence):
        fixes.append("- Add a source-cleaning pass before evidence fallback to remove docs navigation, curl snippets, API-key boilerplate, and pricing/account-tier text.")
    if (payload.get("fact_ledger") or {}).get("contradictions"):
        fixes.append("- Tighten contradiction detection so code snippets and unrelated docs boilerplate do not become semantic conflicts.")
    fixes.append("- Keep the final high-reasoning 64K synthesis path; it is currently the strongest stage in the pipeline.")
    return fixes


def _short(text: str, limit: int = 180) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
