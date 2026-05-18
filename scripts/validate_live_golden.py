"""Validate that a live SYNAPSE artifact is not a toy/demo result."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


FAKE_HOSTS = {"example.com", "localhost", "127.0.0.1", "synthetic.local"}


def _urls(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("search_headers", "fetched_sources", "evidence_items"):
        for item in payload.get(key, []):
            values.append(item.get("url") or item.get("source_url") or "")
    report = payload.get("report_v2") or payload.get("report") or {}
    values.extend(report.get("sources", []))
    return [value for value in values if value]


def _is_fake_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return not parsed.scheme.startswith("http") or host in FAKE_HOSTS or host.endswith(".local") or "example." in host


def _report_text(payload: dict[str, Any]) -> str:
    report = payload.get("report_v2") or payload.get("report") or {}
    sections = " ".join(section.get("content", "") for section in report.get("sections", []))
    findings = " ".join(finding.get("finding", "") for finding in report.get("key_findings", []))
    return " ".join([report.get("answer_summary", ""), sections, findings]).lower()


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    urls = _urls(payload)
    if not urls:
        errors.append("no real URLs exist")
    if urls and all(_is_fake_url(url) for url in urls):
        errors.append("all URLs are fake/local/synthetic")

    fetched = [source for source in payload.get("fetched_sources", []) if source.get("success")]
    if len(fetched) < 3:
        errors.append("fewer than 3 fetched sources exist")

    evidence = payload.get("evidence_items", [])
    if len(evidence) < 5:
        errors.append("fewer than 5 evidence items exist")
    if any(not item.get("source_quote") for item in evidence):
        errors.append("one or more evidence items lack source_quote")

    report = payload.get("report_v2") or payload.get("report") or {}
    for section in report.get("sections", []):
        if section.get("content") and not section.get("used_fact_ids"):
            errors.append(f"report section {section.get('section_id')} lacks fact_ids")

    report_text = _report_text(payload)
    unsupported = (payload.get("fact_ledger") or {}).get("unsupported_claims", [])
    for item in unsupported:
        claim = str(item.get("claim", "")).strip().lower()
        if claim and claim in report_text:
            errors.append(f"unsupported claim appears as true in final report: {claim[:80]}")

    patch_ops = (payload.get("coverage_patch") or {}).get("patch_operations", [])
    for op in patch_ops:
        if not (op.get("fact_ids") or op.get("contradiction_ids") or op.get("result_ids")):
            errors.append("coverage patch operation lacks fact_ids/contradiction_ids/result_ids")

    if patch_ops:
        report_v1 = payload.get("report_v1")
        report_v2 = payload.get("report_v2") or payload.get("report")
        if report_v1 == report_v2:
            errors.append("report_v2 is identical to report_v1 despite patch operations")

    if not payload.get("provider_metrics"):
        errors.append("provider metrics are absent")
    else:
        metrics = payload.get("provider_metrics") or {}
        llm_calls = metrics.get("llm_calls") or []
        text_calls = [call for call in llm_calls if call.get("schema") is None]
        empty_text_calls = [
            call for call in text_calls
            if call.get("response_chars") == 0 or call.get("visible_chars") == 0
        ]
        explicit_synthesis_errors = [
            error for error in payload.get("errors", [])
            if error.get("stage") == "synthesizer"
        ]
        if empty_text_calls and not explicit_synthesis_errors:
            errors.append("synthesizer LLM returned empty visible content")

        # Phase 4.1: Gemini-specific silent-truncation flag.
        gemini_silent_truncation = [
            call for call in llm_calls
            if call.get("provider") == "gemini"
            and call.get("finish_reason") == "MAX_TOKENS"
            and (call.get("visible_chars") == 0 or call.get("truncated_by_reasoning"))
        ]
        if gemini_silent_truncation:
            errors.append("gemini call truncated by reasoning with no visible content (finish_reason=MAX_TOKENS, visible_chars=0)")

        if any(call.get("ok") is True for call in text_calls):
            sections = report.get("sections", [])
            if sections and not any(str(section.get("section_id", "")).startswith("sec_llm_") for section in sections):
                errors.append("synthesis silently fell back to deterministic despite successful LLM calls")

        summary = str(report.get("answer_summary", ""))
        fact_claims = [
            str(fact.get("claim", ""))
            for fact in (payload.get("fact_ledger") or {}).get("verified_facts", [])
            + (payload.get("fact_ledger") or {}).get("partial_facts", [])
        ]
        if summary and fact_claims:
            non_copied_sentences = [
                sentence.strip()
                for sentence in summary.replace("\n", " ").split(".")
                if sentence.strip() and not any(sentence.strip() in claim for claim in fact_claims)
            ]
            if summary.startswith(str(payload.get("research_question", "")) + ":") and not non_copied_sentences:
                errors.append("report summary appears to be deterministic concatenated fact claims")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    args = parser.parse_args()
    payload = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    errors = validate(payload)
    if errors:
        print("Live golden validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Live golden validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
