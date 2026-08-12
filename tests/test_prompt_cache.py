from __future__ import annotations

import os
from pathlib import Path

from backend.prompt_cache import load_cached_result, prompt_hash, store_cached_result


def test_prompt_cache_normalizes_whitespace():
    db = Path("artifacts") / f".test_prompt_cache_{os.getpid()}.sqlite3"
    prompt = "  Compare   A\nand B.  "
    result = {"research_question": "Compare A and B.", "report_v2": {"answer_summary": "Answer."}}

    key = store_cached_result(prompt, result, db_path=db)

    assert key == prompt_hash("Compare A and B.")
    cached = load_cached_result("Compare A and B.", db_path=db)
    assert cached is not None
    assert cached["report_v2"]["answer_summary"] == "Answer."
    assert cached["history"][-1]["mode"] == "prompt_cache"
