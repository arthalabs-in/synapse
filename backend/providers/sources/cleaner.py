"""Source text cleaning and boilerplate filtering."""

import re
from dataclasses import dataclass, field


@dataclass
class CleanedSourceText:
    text: str
    raw_text_chars: int
    clean_text_chars: int
    removed_noise_markers: list[str] = field(default_factory=list)
    failed_quality_filter: bool = False
    cleaning_method: str = "synapse_cleaner"


NOISE_MARKERS = {
    "boilerplate_or_code": [
        "x-goog-api-key",
        "content-type: application/json",
        "rest curl",
        " curl ",
        " -h ",
        " -x post",
        "send feedback",
        "home gemini api docs",
        "skip to main content",
    ],
    "support_page_navigation": [
        "try these next steps",
        "post to the help community",
        "get answers from community members",
        "help 1 of",
        "use gemini apps 2 of",
    ],
    "pricing_or_account_boilerplate": [
        "qualifications for tiers",
        "cumulative spending",
        "billing account linked to your project",
    ],
    "login_shell": [
        "google colab sign in",
        "sign in to continue",
    ],
}


def clean_source_text(raw_text: str, url: str = "", title: str = "") -> CleanedSourceText:
    """Remove recurring navigation/code boilerplate while preserving source prose."""
    del url, title
    raw_lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    raw = " ".join((raw_text or "").split())
    markers = _markers(raw)
    if not raw:
        return CleanedSourceText(text="", raw_text_chars=0, clean_text_chars=0, failed_quality_filter=True)

    line_filtered = []
    for line in raw_lines or [raw]:
        if _looks_like_code(line):
            markers.append("boilerplate_or_code")
            continue
        line_filtered.append(line)
    candidate_text = ". ".join(line_filtered)
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", candidate_text) if sentence.strip()]
    if not sentences:
        sentences = [raw]

    kept = []
    for sentence in sentences:
        if _sentence_is_noise(sentence):
            continue
        if _looks_like_code(sentence):
            markers.append("boilerplate_or_code")
            continue
        kept.append(sentence)

    text = " ".join(kept).strip()
    markers = sorted(set(markers))
    failed = _failed_quality_filter(text, markers)
    if failed:
        text = ""
    return CleanedSourceText(
        text=text,
        raw_text_chars=len(raw),
        clean_text_chars=len(text),
        removed_noise_markers=markers,
        failed_quality_filter=failed,
    )


def _markers(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for marker_name, needles in NOISE_MARKERS.items():
        if any(needle in lowered for needle in needles):
            found.append(marker_name)
    return found


def _sentence_is_noise(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(needle in lowered for needles in NOISE_MARKERS.values() for needle in needles)


def _looks_like_code(sentence: str) -> bool:
    lowered = sentence.lower()
    if sentence.count("\\") >= 2 or sentence.count("{") >= 2:
        return True
    return "gemini_api_key" in lowered or "$gemini_api_key" in lowered


def _failed_quality_filter(text: str, markers: list[str]) -> bool:
    if not text:
        return True
    if ("support_page_navigation" in markers or "login_shell" in markers) and len(text.split()) < 20:
        return True
    return False
