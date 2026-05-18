"""Run a live SYNAPSE profile and save operation/LLM timing data."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.research_engine import SynapseResearchEngine


async def _run(query: str, timeout: int, out_path: Path, trace_path: Path) -> tuple[dict[str, Any], int]:
    engine = SynapseResearchEngine(demo_mode=False)
    try:
        result = await asyncio.wait_for(engine.run(query), timeout=timeout)
        payload = result.model_dump(mode="json")
        payload["profile_status"] = "completed"
        _write_json(out_path, payload)
        _write_markdown(trace_path, payload)
        return payload, 0
    except Exception as exc:
        payload = {
            "profile_status": "failed",
            "query": query,
            "stage": getattr(engine, "current_stage", "unknown"),
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            "profile_events": getattr(engine, "profile_events", []),
            "provider_metrics": engine._provider_metrics(),
        }
        _write_json(out_path, payload)
        _write_markdown(trace_path, payload)
        return payload, 1


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = payload.get("provider_metrics") or {}
    llm_calls = metrics.get("llm_calls", [])
    events = payload.get("profile_events") or metrics.get("profile_events", [])
    search_events = metrics.get("search_events", [])
    fetch_events = metrics.get("source_fetch_events", [])

    lines = [
        "# SYNAPSE Live Profile",
        "",
        f"Status: `{payload.get('profile_status')}`",
        f"Stage: `{payload.get('stage', payload.get('history', [{}])[-1].get('stage', 'complete'))}`",
        f"Error: `{payload.get('error', '')}`",
        "",
        "## Operation Wall Time",
        "| Operation | OK | Seconds | Wall Start | Wall End |",
        "|---|---:|---:|---|---|",
    ]
    for event in events:
        lines.append(
            f"| {event.get('operation')} | {event.get('ok')} | {event.get('seconds')} | "
            f"{event.get('wall_start')} | {event.get('wall_end')} |"
        )

    lines.extend(
        [
            "",
            "## LLM Calls",
            f"Total LLM calls: **{len(llm_calls)}**",
            "| # | Schema | OK | Seconds | Prompt | Completion | Total | Wall Start | Wall End | Error |",
            "|---:|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for call in llm_calls:
        seconds = round((call.get("latency_ms") or 0) / 1000, 3)
        lines.append(
            f"| {call.get('call_index')} | {call.get('schema')} | {call.get('ok')} | {seconds} | "
            f"{call.get('prompt_tokens')} | {call.get('completion_tokens')} | {call.get('total_tokens')} | "
            f"{call.get('wall_start')} | {call.get('wall_end')} | {call.get('error', '')} |"
        )

    lines.extend(["", "## Search Provider Calls", "| Provider | OK | Seconds | Results | Query |", "|---|---:|---:|---:|---|"])
    for event in search_events:
        query = str(event.get("query", ""))[:120].replace("|", "\\|")
        lines.append(f"| {event.get('provider')} | {event.get('ok')} | {event.get('seconds')} | {event.get('result_count')} | {query} |")

    lines.extend(["", "## Source Fetch Calls", "| Status | OK | Seconds | Chars | URL | Error |", "|---|---:|---:|---:|---|---|"])
    for event in fetch_events:
        url = str(event.get("url", ""))[:100].replace("|", "\\|")
        error = str(event.get("error") or "")[:120].replace("|", "\\|")
        lines.append(f"| {event.get('fetch_status')} | {event.get('success')} | {event.get('seconds')} | {event.get('text_chars')} | {url} | {error} |")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--out", default="artifacts/live_profile.json")
    parser.add_argument("--trace", default="artifacts/live_profile.md")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    payload, code = asyncio.run(_run(args.query, args.timeout, Path(args.out), Path(args.trace)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
