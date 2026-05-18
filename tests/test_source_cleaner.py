from backend.providers.sources.cleaner import clean_source_text


def test_clean_source_text_removes_curl_and_api_key_boilerplate():
    raw = """
    Home Gemini API Docs Send feedback Function calling with the Gemini API
    REST curl "https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY" -H 'Content-Type: application/json' -X POST
    Function calling lets Gemini models connect to external tools and APIs.
    """

    result = clean_source_text(raw, url="https://ai.google.dev/gemini-api/docs/function-calling", title="Function calling")

    assert "x-goog-api-key" not in result.text
    assert "REST curl" not in result.text
    assert "Send feedback" not in result.text
    assert "Function calling lets Gemini models connect to external tools and APIs." in result.text
    assert "boilerplate_or_code" in result.removed_noise_markers


def test_clean_source_text_rejects_source_that_is_only_navigation():
    raw = "Try these next steps: Post to the help community Get answers from community members Help 1 of 18 Use Gemini Apps 2 of 18"

    result = clean_source_text(raw, url="https://support.google.com/gemini/answer/16596215", title="Gemini support")

    assert result.text == ""
    assert result.failed_quality_filter is True
    assert "support_page_navigation" in result.removed_noise_markers


def test_clean_source_text_rejects_colab_sign_in_shell():
    result = clean_source_text("Google Colab Sign in", url="https://colab.research.google.com/x.ipynb", title="Notebook")

    assert result.text == ""
    assert result.failed_quality_filter is True
    assert "login_shell" in result.removed_noise_markers


def test_clean_source_text_keeps_arxiv_style_summary():
    raw = "We present an evaluation framework for multi-turn agents. The framework measures tool-use accuracy and task completion."

    result = clean_source_text(raw, url="https://arxiv.org/abs/2501.12345", title="Agent evaluation")

    assert result.text == raw
    assert result.failed_quality_filter is False
    assert result.removed_noise_markers == []
