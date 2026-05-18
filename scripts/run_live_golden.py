"""Run a live SYNAPSE pipeline trace and save proof artifacts."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.research_engine import SynapseResearchEngine


async def _run_and_write(query: str, out_path: Path, trace_path: Path, timeout: int) -> int:
    engine = SynapseResearchEngine(demo_mode=False)
    try:
        result = await asyncio.wait_for(engine.run(query), timeout=timeout)
        payload = result.model_dump(mode="json")
        _write_json(out_path, payload)
        _write_trace(trace_path, payload)
        return 0
    except asyncio.TimeoutError as exc:
        stage = getattr(engine, "current_stage", "unknown")
        failure = {
            "query": query,
            "failed": True,
            "error": f"timed out while running stage: {stage}",
            "stage": "TimeoutError",
            "provider_metrics": engine._provider_metrics(),
        }
        _write_json(out_path, failure)
        _write_trace(trace_path, failure, failed_stage=failure["stage"])
        return 1
    except Exception as exc:
        failure = {
            "query": query,
            "failed": True,
            "error": str(exc),
            "stage": exc.__class__.__name__,
            "provider_metrics": engine._provider_metrics(),
        }
        _write_json(out_path, failure)
        _write_trace(trace_path, failure, failed_stage=failure["stage"])
        return 1


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_trace(path: Path, payload: dict[str, Any], failed_stage: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# SYNAPSE Live Golden Trace", ""]
    if failed_stage:
        lines.extend([f"Live run failed at: `{failed_stage}`", ""])
    lines.extend([f"## Query", payload.get("research_question", payload.get("query", "")), ""])

    planner = payload.get("planner_precontext") or {}
    lines.extend(["## Planner Precontext Sources"])
    for claim in planner.get("precontext_claims", []):
        lines.append(f"- {claim.get('claim')} ({claim.get('url')})")

    lines.extend(["", "## Research Jobs"])
    for job in planner.get("research_jobs", []):
        lines.append(f"- {job.get('job_id')}: {job.get('objective')}")

    lines.extend(["", "## Search Headers"])
    for header in payload.get("search_headers", []):
        lines.append(f"- [{header.get('provider')}] {header.get('title')} - {header.get('url')}")

    lines.extend(["", "## Fetched Sources"])
    for source in payload.get("fetched_sources", []):
        lines.append(f"- {source.get('fetch_status')}: {source.get('title') or source.get('url')}")

    run_quality = payload.get("run_quality") or {}
    if run_quality:
        signals = run_quality.get("signals") or {}
        lines.extend(
            [
                "",
                "## Run Quality",
                f"- Grade: {run_quality.get('grade')} ({run_quality.get('score')})",
                f"- Evidence: {signals.get('evidence_count')} total, {signals.get('llm_evidence_count')} LLM, {signals.get('fallback_evidence_count')} fallback",
                f"- Sources: {signals.get('successful_fetched_source_count')}/{signals.get('fetched_source_count')} fetched successfully",
                f"- Fallback reasons: {run_quality.get('fallback_reasons') or {}}",
            ]
        )

    lines.extend(["", "## Evidence Items"])
    for item in payload.get("evidence_items", []):
        quote = (item.get("source_quote") or "")[:280]
        fallback = f" | fallback_reason={item.get('fallback_reason')}" if item.get("fallback_reason") else ""
        lines.append(
            f"- {item.get('evidence_id')}: method={item.get('extraction_method')}{fallback} | "
            f"{item.get('claim')} | Quote: \"{quote}\""
        )

    ledger = payload.get("fact_ledger") or {}
    lines.extend(
        [
            "",
            "## Fact Ledger Summary",
            f"- Verified: {len(ledger.get('verified_facts', []))}",
            f"- Partial: {len(ledger.get('partial_facts', []))}",
            f"- Unsupported: {len(ledger.get('unsupported_claims', []))}",
            f"- Contradictions: {len(ledger.get('contradictions', []))}",
            "",
            "## Report v1 Summary",
            (payload.get("report_v1") or {}).get("answer_summary", ""),
            "",
            "## Coverage Diff / Patch Operations",
        ]
    )
    patch = payload.get("coverage_patch") or {}
    for op in patch.get("patch_operations", []):
        refs = op.get("fact_ids") or op.get("contradiction_ids") or op.get("result_ids")
        location = op.get("target_path") or op.get("target_section_id") or "report"
        label = op.get("edit_label") or op.get("edit_id") or op.get("op")
        lines.append(f"- {op.get('op')}: {label} | location={location} | reason={op.get('reason')} refs={refs}")
        if op.get("original_text") or op.get("replacement_text"):
            lines.append(f"  - before: {op.get('original_text') or ''}")
            lines.append(f"  - after: {op.get('replacement_text') or op.get('text') or ''}")

    lines.extend(
        [
            "",
            "## Report v2 Summary",
            (payload.get("report_v2") or payload.get("report") or {}).get("answer_summary", ""),
            "",
            "## Degraded Mode Warnings",
        ]
    )
    for error in payload.get("errors", []):
        lines.append(f"- {error.get('stage')}: {error.get('error')}")
    if not payload.get("errors"):
        lines.append("- none")

    lines.extend(["", "## Provider Metrics And Timings"])
    lines.append(f"```json\n{json.dumps({'provider_metrics': payload.get('provider_metrics'), 'timings': payload.get('timings')}, indent=2)}\n```")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()

    out_path = Path(args.out)
    trace_path = Path(args.trace)

    return asyncio.run(_run_and_write(args.query, out_path, trace_path, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
