"""Seed the SQLite prompt cache from an existing pipeline result artifact."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.prompt_cache import DEFAULT_CACHE_PATH, store_cached_result_from_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--db", default=str(DEFAULT_CACHE_PATH))
    args = parser.parse_args()

    key = store_cached_result_from_file(args.prompt, Path(args.result), db_path=Path(args.db))
    print(f"Cached prompt {key[:12]} in {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
