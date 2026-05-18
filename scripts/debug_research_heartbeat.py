"""Run SYNAPSE with periodic stage heartbeats for live debugging."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.research_engine import SynapseResearchEngine


async def _heartbeat(engine: SynapseResearchEngine, seconds: int) -> None:
    while True:
        await asyncio.sleep(seconds)
        events = getattr(engine, "profile_events", [])
        print(
            json.dumps(
                {
                    "heartbeat_stage": getattr(engine, "current_stage", "unknown"),
                    "profile_event_count": len(events),
                    "last_events": events[-3:],
                    "llm_call_count": len(getattr(engine.llm_provider, "call_log", [])) if engine.llm_provider else 0,
                },
                default=str,
            ),
            flush=True,
        )


async def _run(query: str, out_path: Path, timeout: int, heartbeat_seconds: int) -> int:
    engine = SynapseResearchEngine(demo_mode=False)
    monitor = asyncio.create_task(_heartbeat(engine, heartbeat_seconds))
    try:
        result = await asyncio.wait_for(engine.run(query), timeout=timeout)
        _write_json(out_path, result.model_dump(mode="json"))
        return 0
    except Exception as exc:
        payload: dict[str, Any] = {
            "failed": True,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            "stage": getattr(engine, "current_stage", "unknown"),
            "profile_events": getattr(engine, "profile_events", []),
            "provider_metrics": engine._provider_metrics(),
        }
        _write_json(out_path, payload)
        return 1
    finally:
        monitor.cancel()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--heartbeat", type=int, default=10)
    args = parser.parse_args()
    return asyncio.run(_run(args.query, Path(args.out), args.timeout, args.heartbeat))


if __name__ == "__main__":
    raise SystemExit(main())
