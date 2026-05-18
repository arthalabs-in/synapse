"""Regenerate the checked-in Gemini golden fixture from a real live run.

Phase 4.2: run this script after merging a feature that materially changes
    pipeline behavior to refresh ``tests/fixtures/uoe_golden.json``.
Deterministic tests still read the checked-in fixture; this script is for
post-merge regeneration only.

Example:
    python scripts/refresh_golden_fixture.py \\
        --query "Which Gemini-first, evidence-grounded AI agent workflow..." \\
        --out tests/fixtures/uoe_golden.json \\
        --timeout 360
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.research_engine import SynapseResearchEngine
from config import config


async def _refresh(query: str, out_path: Path, timeout: int) -> int:
    engine = SynapseResearchEngine(demo_mode=False)
    try:
        result = await asyncio.wait_for(engine.run(query), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"[refresh_golden_fixture] live run timed out at stage: {getattr(engine, 'current_stage', 'unknown')}")
        return 1
    except Exception as exc:
        print(f"[refresh_golden_fixture] live run failed: {exc}")
        return 1

    payload = result.model_dump(mode="json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[refresh_golden_fixture] wrote {out_path} ({out_path.stat().st_size} bytes)")
    # Surface a tiny sanity check so the operator notices a degraded result.
    print(f"[refresh_golden_fixture] evidence_items={len(payload.get('evidence_items', []))}, "
          f"verified={len((payload.get('fact_ledger') or {}).get('verified_facts', []))}, "
          f"degraded={payload.get('degraded')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the checked-in Gemini golden fixture from a live run.")
    parser.add_argument(
        "--query",
        default=config.DEMO_QUERY,
        help="Query to run (defaults to config.DEMO_QUERY).",
    )
    parser.add_argument(
        "--out",
        default="tests/fixtures/uoe_golden.json",
        help="Fixture path to overwrite.",
    )
    parser.add_argument("--timeout", type=int, default=360, help="Seconds before the run aborts.")
    args = parser.parse_args()

    return asyncio.run(_refresh(args.query, Path(args.out), args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
