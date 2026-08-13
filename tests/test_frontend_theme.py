from frontend import theme
from pathlib import Path


APP_SOURCE = Path("frontend/app.py").read_text(encoding="utf-8")


def test_editorial_light_tokens_are_present():
    assert "--paper: #f3f0e8" in theme._CSS
    assert "--surface: #fbfaf6" in theme._CSS
    assert "--accent: #3157d5" in theme._CSS
    assert "Newsreader" in theme._CSS


def test_dark_dashboard_decoration_is_removed():
    assert "radial-gradient" not in theme._CSS
    assert "background-size: 42px 42px" not in theme._CSS


def test_wordmark_uses_enlarged_signal_slash():
    assert 'class="syn-logo-slash"' in theme.wordmark()
    assert ".syn-logo-slash" in theme._CSS
    assert "height: 3px" in theme._CSS


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion: reduce" in theme._CSS


def test_result_workspace_is_report_first():
    assert 'st.columns([0.20, 0.80], gap="large")' in APP_SOURCE
    assert 'st.columns([0.64, 0.36], gap="large")' in APP_SOURCE


def test_evidence_strip_has_a_display_limit():
    assert "def render_evidence_strip(result: dict[str, Any], limit: int = 6)" in APP_SOURCE
    assert "items[:limit]" in APP_SOURCE
    assert "visible_count = 1 if limit <= 3 else 3" in APP_SOURCE
