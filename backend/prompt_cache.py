"""SQLite cache for completed prompt runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


DEFAULT_CACHE_PATH = Path("artifacts") / "prompt_cache.sqlite3"


def normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().split())


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(normalize_prompt(prompt).encode("utf-8")).hexdigest()


def init_prompt_cache(db_path: str | Path = DEFAULT_CACHE_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_cache (
                prompt_hash TEXT PRIMARY KEY,
                prompt_text TEXT NOT NULL,
                result_json TEXT NOT NULL,
                source_path TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
    return path


def load_cached_result(prompt: str, db_path: str | Path = DEFAULT_CACHE_PATH) -> dict[str, Any] | None:
    path = init_prompt_cache(db_path)
    key = prompt_hash(prompt)
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT result_json FROM prompt_cache WHERE prompt_hash = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    data = json.loads(row[0])
    data.setdefault("history", []).append({"mode": "prompt_cache", "prompt_hash": key[:12]})
    return data


def store_cached_result(
    prompt: str,
    result: dict[str, Any],
    *,
    source_path: str | Path | None = None,
    db_path: str | Path = DEFAULT_CACHE_PATH,
) -> str:
    path = init_prompt_cache(db_path)
    normalized = normalize_prompt(prompt)
    key = prompt_hash(normalized)
    now = time.time()
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO prompt_cache (
                prompt_hash, prompt_text, result_json, source_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(prompt_hash) DO UPDATE SET
                prompt_text = excluded.prompt_text,
                result_json = excluded.result_json,
                source_path = excluded.source_path,
                updated_at = excluded.updated_at
            """,
            (key, normalized, payload, str(source_path) if source_path else None, now, now),
        )
    return key


def store_cached_result_from_file(
    prompt: str,
    result_path: str | Path,
    *,
    db_path: str | Path = DEFAULT_CACHE_PATH,
) -> str:
    path = Path(result_path)
    result = json.loads(path.read_text(encoding="utf-8"))
    return store_cached_result(prompt, result, source_path=path, db_path=db_path)
