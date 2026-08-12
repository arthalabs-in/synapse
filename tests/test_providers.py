import asyncio
import json
import time
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import BaseModel

from backend.models import FetchedSource, SearchHeader
from backend.providers.llm.factory import create_llm_provider
from backend.providers.llm.gemini import GeminiProvider
from backend.providers.llm.openai_compatible import EmptyVisibleContentError, OpenAICompatibleProvider
from backend.providers.llm.opencode_go import OpenCodeGoProvider
from backend.providers.search.base import SearchProviderError
from backend.providers.search.arxiv_provider import ArxivProvider
from backend.providers.search.composite_search import CompositeSearchProvider
from backend.providers.search.duckduckgo_provider import DuckDuckGoProvider
from backend.providers.sources.fetcher import SourceFetcher


def test_duckduckgo_provider_maps_results():
    provider = DuckDuckGoProvider(ddgs_factory=FakeDDGS)

    results = asyncio.run(provider.search("mi300x", max_results=1))

    assert results[0].provider == "duckduckgo"
    assert results[0].title == "AMD MI300X"
    assert results[0].url.startswith("https://www.amd.com")


def test_duckduckgo_timeout_does_not_wait_for_blocking_worker_shutdown():
    provider = DuckDuckGoProvider(ddgs_factory=SlowDDGS, timeout_seconds=0.05)

    start = time.monotonic()
    with pytest.raises(SearchProviderError):
        asyncio.run(provider.search("mi300x", max_results=1))
    elapsed = time.monotonic() - start

    assert elapsed < 0.7


def test_duckduckgo_default_provider_uses_subprocess_path(monkeypatch):
    provider = DuckDuckGoProvider()
    called = {"subprocess": False}

    async def fake_subprocess(query, max_results):
        called["subprocess"] = True
        return [
            SearchHeader(
                result_id="ddg_subprocess_1",
                query=query,
                title="Subprocess result",
                url="https://example.com/subprocess",
                snippet="Result from isolated subprocess.",
                rank=1,
                provider="duckduckgo",
            )
        ]

    monkeypatch.setattr(provider, "_search_in_subprocess", fake_subprocess)

    results = asyncio.run(provider.search("mi300x", max_results=1))

    assert called["subprocess"] is True
    assert results[0].title == "Subprocess result"


def test_arxiv_provider_maps_metadata():
    provider = ArxivProvider(client_factory=FakeArxivClient)

    results = asyncio.run(provider.search("llm inference", max_results=1))

    assert results[0].provider == "arxiv"
    assert results[0].source_type_guess == "paper"
    assert results[0].arxiv_id == "2401.12345"
    assert results[0].metadata["authors"] == ["Researcher One"]


def test_composite_search_deduplicates_by_url():
    same = SearchHeader(result_id="a", query="q", title="A", url="https://www.amd.com/x", snippet="one", rank=1, provider="a")
    duplicate = SearchHeader(result_id="b", query="q", title="B", url="https://www.amd.com/x/", snippet="two", rank=2, provider="b")
    provider = CompositeSearchProvider([StaticProvider([same]), StaticProvider([duplicate])])

    results = asyncio.run(provider.search("q", max_results=5))

    assert len(results) == 1


def test_source_fetcher_uses_camofox_for_short_http_text():
    header = SearchHeader(result_id="res_1", query="q", title="Title", url="https://www.amd.com/x", snippet="snippet", rank=1)
    fetcher = SourceFetcher(
        html_fetcher=StaticHttpFetcher(FetchedSource(source_id="src_1", result_id="res_1", url=header.url, text="short", provider="http", fetch_status="fetched_http", success=True)),
        camofox_client=StaticCamofox(FetchedSource(source_id="src_1", result_id="res_1", url=header.url, text="long enough from browser", provider="camofox", fetch_status="fetched_camofox", success=True)),
        min_text_chars=50,
    )

    results = asyncio.run(fetcher.fetch_many([header]))

    assert results[0].fetch_status == "fetched_camofox"
    assert fetcher.summary["fetched_camofox_count"] == 1


def test_source_fetcher_arxiv_metadata_only_success():
    header = SearchHeader(
        result_id="arxiv_2401.12345",
        query="q",
        title="Paper",
        url="https://arxiv.org/abs/2401.12345",
        snippet="summary",
        rank=1,
        provider="arxiv",
        metadata={"summary": "paper summary"},
        arxiv_id="2401.12345",
    )

    source = asyncio.run(SourceFetcher().fetch_one(header))

    assert source.fetch_status == "arxiv_metadata_only"
    assert source.success is True


def test_source_fetcher_fetches_duplicate_urls_once_when_requests_overlap():
    first = SearchHeader(result_id="res_1", query="q", title="First", url="https://example.com/same", snippet="snippet", rank=1)
    second = SearchHeader(result_id="res_2", query="q", title="Second", url="https://example.com/same", snippet="snippet", rank=2)
    http_fetcher = CountingHttpFetcher()
    fetcher = SourceFetcher(
        html_fetcher=http_fetcher,
        camofox_client=StaticCamofox(FetchedSource(source_id="unused", result_id="unused", url=first.url)),
    )

    results = asyncio.run(fetcher.fetch_many([first, second]))

    assert http_fetcher.calls == 1
    assert len(results) == 2
    assert results[0] is results[1]


def test_openai_compatible_provider_parses_json_and_usage():
    class Payload(BaseModel):
        answer: str

    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer":"ok"}'}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        api_key="key",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_json([{"role": "user", "content": "hi"}], Payload))

    assert response.parsed_json == {"answer": "ok"}
    assert response.usage.total_tokens == 7
    assert provider.token_usage["total_tokens"] == 7


def test_openai_compatible_provider_retries_invalid_json():
    class Payload(BaseModel):
        answer: str

    calls = {"count": 0}

    async def handler(request):
        calls["count"] += 1
        content = "not json" if calls["count"] == 1 else '{"answer":"fixed"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_json([{"role": "user", "content": "hi"}], Payload))

    assert response.parsed_json == {"answer": "fixed"}
    assert calls["count"] == 2


def test_openai_compatible_raises_on_empty_visible_content_with_usage():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "", "reasoning_content": "private reasoning"},
                        "finish_reason": "length",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 900,
                    "total_tokens": 1000,
                    "completion_tokens_details": {"reasoning_tokens": 900},
                },
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmptyVisibleContentError) as exc:
        asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}], max_tokens=900))

    assert exc.value.reasoning_tokens == 900
    assert provider.call_log[-1]["finish_reason"] == "length"
    assert provider.call_log[-1]["truncated_by_reasoning"] is True
    assert provider.call_log[-1]["visible_chars"] == 0


def test_openai_compatible_extracts_list_content_parts():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "hello "},
                                {"type": "text", "text": "world"},
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}]))

    assert response.text == "hello world"


def test_openai_compatible_passes_reasoning_effort():
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(
        provider.chat_text(
            [{"role": "user", "content": "hi"}],
            reasoning_effort="minimal",
            reasoning={"max_tokens": 64},
        )
    )

    assert seen["reasoning_effort"] == "minimal"
    assert seen["reasoning"] == {"max_tokens": 64}


def test_openai_compatible_injects_skill_blocks_as_system_message():
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}], skills=["Evidence-First synthesis"]))

    assert seen["messages"][0]["role"] == "system"
    assert "Evidence-First synthesis" in seen["messages"][0]["content"]
    assert provider.call_log[-1]["skill_count"] == 1


def test_openai_compatible_records_reasoning_tokens_in_usage():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "completion_tokens_details": {"reasoning_tokens": 12},
                },
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}]))

    assert response.usage.reasoning_tokens == 12
    assert provider.call_log[-1]["reasoning_tokens"] == 12


def test_gemini_provider_posts_generate_content_and_parses_json_usage():
    class Payload(BaseModel):
        answer: str

    seen = []

    async def handler(request):
        seen.append(request)
        assert request.url.path == "/v1beta/models/gemini-2.5-pro:generateContent"
        assert request.headers["x-goog-api-key"] == "secret"
        body = request.read().decode()
        assert '"responseMimeType":"application/json"' in body
        assert '"maxOutputTokens":256' in body
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": '{"answer":"ok"}'}]}}],
                "usageMetadata": {
                    "promptTokenCount": 3,
                    "candidatesTokenCount": 4,
                    "totalTokenCount": 7,
                },
            },
        )

    provider = GeminiProvider(
        api_key="secret",
        model="gemini-2.5-pro",
        transport=httpx.MockTransport(handler),
    )

    response = asyncio.run(provider.chat_json([{"role": "user", "content": "hi"}], Payload, max_tokens=256))

    assert response.parsed_json == {"answer": "ok"}
    assert response.provider == "gemini"
    assert response.usage.total_tokens == 7
    assert provider.token_usage["total_tokens"] == 7
    assert provider.call_log[0]["ok"] is True


def test_gemini_provider_injects_skill_blocks_into_system_instruction():
    seen = {}

    async def handler(request):
        seen.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2, "totalTokenCount": 3},
            },
        )

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))

    asyncio.run(provider.chat_text([{"role": "user", "content": "hi"}], skills=["Evidence-First synthesis"]))

    system_text = seen["systemInstruction"]["parts"][0]["text"]
    assert "Evidence-First synthesis" in system_text
    assert provider.call_log[-1]["skill_count"] == 1


def test_gemini_provider_retries_invalid_json():
    class Payload(BaseModel):
        answer: str

    calls = {"count": 0}

    async def handler(request):
        calls["count"] += 1
        content = "not json" if calls["count"] == 1 else '{"answer":"fixed"}'
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": content}]}}]})

    provider = GeminiProvider(api_key="secret", model="gemini-2.5-pro", transport=httpx.MockTransport(handler))

    response = asyncio.run(provider.chat_json([{"role": "user", "content": "hi"}], Payload))

    assert response.parsed_json == {"answer": "fixed"}
    assert calls["count"] == 2


def test_llm_factory_routes_only_gemini_and_temporary_opencode(monkeypatch):
    monkeypatch.setattr("backend.providers.llm.factory.config.LLM_PROVIDER", "gemini")
    assert create_llm_provider().__class__.__name__ == "GeminiProvider"

    monkeypatch.setattr("backend.providers.llm.factory.config.LLM_PROVIDER", "opencode_go")
    assert create_llm_provider().__class__.__name__ == "OpenCodeGoProvider"

    monkeypatch.setattr("backend.providers.llm.factory.config.LLM_PROVIDER", "vllm")
    with pytest.raises(ValueError, match="unsupported LLM_PROVIDER"):
        create_llm_provider()


def test_opencode_go_provider_builds_endpoint_auth_and_model():
    provider = OpenCodeGoProvider(base_url="https://opencode.test/v1", api_key="secret", model="qwen")

    assert provider.base_url == "https://opencode.test/v1"
    assert provider.model == "qwen"
    assert provider.auth_header == "Authorization"
    assert provider.auth_scheme == "Bearer"


class FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, region, safesearch, max_results):
        return [{"title": "AMD MI300X", "href": "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html", "body": "Official MI300X page."}]


class SlowDDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, region, safesearch, max_results):
        time.sleep(1.2)
        return []


class FakeArxivClient:
    def results(self, search):
        yield FakePaper()


class FakePaper:
    entry_id = "https://arxiv.org/abs/2401.12345"
    pdf_url = "https://arxiv.org/pdf/2401.12345"
    published = datetime(2024, 1, 1, tzinfo=timezone.utc)
    updated = datetime(2024, 1, 2, tzinfo=timezone.utc)
    authors = ["Researcher One"]
    categories = ["cs.LG"]
    primary_category = "cs.LG"
    title = "Inference Paper"
    summary = "Paper summary."


class StaticProvider:
    def __init__(self, results):
        self.results = results

    async def search(self, query, max_results=5, **kwargs):
        return self.results


class StaticHttpFetcher:
    def __init__(self, source):
        self.source = source

    async def fetch(self, header):
        return self.source


class CountingHttpFetcher:
    def __init__(self):
        self.calls = 0

    async def fetch(self, header):
        self.calls += 1
        await asyncio.sleep(0)
        return FetchedSource(
            source_id=f"src_{header.result_id}",
            result_id=header.result_id,
            url=header.url,
            text="enough source text",
            provider="http",
            fetch_status="fetched_http",
            success=True,
        )


class StaticCamofox:
    def __init__(self, source):
        self.source = source

    async def fetch(self, header):
        return self.source
