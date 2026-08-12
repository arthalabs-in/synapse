from scripts.validate_live_golden import validate


def test_validator_accepts_realistic_live_artifact():
    payload = make_payload()

    assert validate(payload) == []


def test_validator_rejects_fake_urls():
    payload = make_payload()
    for header in payload["search_headers"]:
        header["url"] = "https://example.com/source"
    for source in payload["fetched_sources"]:
        source["url"] = "https://example.com/source"
    for item in payload["evidence_items"]:
        item["source_url"] = "https://example.com/source"
    payload["report_v2"]["sources"] = ["https://example.com/source"]

    errors = validate(payload)

    assert "all URLs are fake/local/synthetic" in errors


def test_validator_rejects_too_few_evidence_items():
    payload = make_payload()
    payload["evidence_items"] = payload["evidence_items"][:2]

    assert "fewer than 5 evidence items exist" in validate(payload)


def test_validator_rejects_patch_without_references():
    payload = make_payload()
    payload["coverage_patch"]["patch_operations"][0]["fact_ids"] = []

    assert "coverage patch operation lacks fact_ids/contradiction_ids/result_ids" in validate(payload)


def test_validator_fails_when_synthesis_llm_returned_empty_text():
    payload = make_payload()
    payload["provider_metrics"] = {
        "llm_calls": [{"schema": None, "ok": False, "response_chars": 0, "visible_chars": 0}],
    }

    assert "synthesizer LLM returned empty visible content" in validate(payload)


def test_validator_fails_when_llm_synthesis_silently_fell_back_to_deterministic_sections():
    payload = make_payload()
    payload["provider_metrics"] = {
        "llm_calls": [{"schema": None, "ok": True, "response_chars": 120, "visible_chars": 120}],
    }
    payload["report_v2"]["sections"] = [
        {"section_id": "sec_verified", "content": "Claim 0", "used_fact_ids": ["fact_0"]}
    ]

    assert "synthesis silently fell back to deterministic despite successful LLM calls" in validate(payload)


def make_payload():
    urls = [
        "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
        "https://www.nvidia.com/en-us/data-center/h100/",
        "https://docs.vllm.ai/en/latest/",
    ]
    evidence = [
        {
            "evidence_id": f"ev_{index}",
            "claim": f"Claim {index}",
            "source_url": urls[index % len(urls)],
            "source_quote": f"Grounded source quote {index}",
        }
        for index in range(5)
    ]
    report_v1 = {
        "answer_summary": "Claim 0",
        "sections": [{"section_id": "s1", "content": "Claim 0", "used_fact_ids": ["fact_0"]}],
        "key_findings": [],
        "sources": urls,
    }
    report_v2 = {
        "answer_summary": "Claim 0 with added verified detail.",
        "sections": [{"section_id": "s1", "content": "Claim 0 with added verified detail.", "used_fact_ids": ["fact_0", "fact_1"]}],
        "key_findings": [],
        "sources": urls,
    }
    return {
        "research_question": "Compare GPUs",
        "search_headers": [{"url": url} for url in urls],
        "fetched_sources": [{"url": url, "success": True} for url in urls],
        "evidence_items": evidence,
        "fact_ledger": {"unsupported_claims": [{"claim": "This unsupported sentence is absent."}]},
        "coverage_patch": {"patch_operations": [{"op": "add", "fact_ids": ["fact_1"]}]},
        "report_v1": report_v1,
        "report_v2": report_v2,
        "provider_metrics": {"search_provider": "composite"},
    }




def test_validator_flags_gemini_silent_truncation():
    import json
    from pathlib import Path

    fixture = Path("tests/fixtures/invalid_gemini_silent_truncation.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    errors = validate(payload)

    assert any(
        "gemini call truncated by reasoning" in error
        for error in errors
    ), f"expected gemini silent-truncation flag, got: {errors}"
