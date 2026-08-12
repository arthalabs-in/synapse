"""Load local agent skills for prompt injection."""

from functools import lru_cache
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parent / "skills"


@lru_cache(maxsize=8)
def load_agent_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()
