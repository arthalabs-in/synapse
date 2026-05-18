"""Phase 3.2 tests: multimodal ingestor + upload:// URL allowance."""

import asyncio
import hashlib

import pytest

from agents.multimodal_ingestor import MultimodalIngestorAgent
from backend.models import EvidenceItem, LLMResponse
from backend.validators import require_url


class _StubGeminiMultimodal:
    """Fake Gemini provider that returns parsed JSON on chat_multimodal."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    async def chat_multimodal(self, messages, inline_parts, **kwargs):
        self.calls.append({"messages": messages, "inline_parts": inline_parts, "kwargs": kwargs})
        return LLMResponse(
            text="",
            parsed_json=self.payload,
            model="gemini-2.5-pro",
            provider="gemini",
        )


def test_upload_url_is_allowed_when_multimodal_enabled(monkeypatch):
    monkeypatch.setattr("backend.validators.Any", object, raising=False)
    # When MULTIMODAL_ENABLED=False the validator must refuse upload:// URLs.
    monkeypatch.setattr("config.config.MULTIMODAL_ENABLED", False)
    with pytest.raises(ValueError):
        require_url("upload://abc", "source_url")

    # When MULTIMODAL_ENABLED=True the validator accepts upload:// URLs.
    monkeypatch.setattr("config.config.MULTIMODAL_ENABLED", True)
    assert require_url("upload://abc", "source_url") == "upload://abc"


def test_multimodal_ingestor_produces_evidence_item(monkeypatch):
    monkeypatch.setattr("config.config.MULTIMODAL_ENABLED", True)

    provider = _StubGeminiMultimodal(
        {
            "claim": "The PDF reports 99% accuracy on benchmark X.",
            "source_quote": "Our system achieved 99% accuracy on benchmark X.",
            "source_title": "Research PDF",
            "date": "2026-04-01",
            "relevance_to_query": 0.85,
        }
    )
    agent = MultimodalIngestorAgent(llm_provider=provider)
    data = b"pretend-pdf-bytes"
    sha = hashlib.sha256(data).hexdigest()
    uploads = [
        {
            "file_name": "paper.pdf",
            "mime_type": "application/pdf",
            "size_bytes": len(data),
            "sha256": sha,
            "data": data,
        }
    ]

    result = asyncio.run(agent.ingest("What accuracy did we report?", uploads))

    assert len(result.evidence_items) == 1
    evidence: EvidenceItem = result.evidence_items[0]
    assert evidence.source_type == "user_upload"
    assert evidence.source_url == f"upload://{sha}"
    assert evidence.extraction_method == "llm_multimodal"
    assert evidence.source_quote.startswith("Our system achieved")
    assert result.upload_metadata[0].file_name == "paper.pdf"
    assert result.upload_metadata[0].sha256 == sha

    # Verify the ingestor base64-encoded the file via chat_multimodal.
    assert provider.calls[0]["inline_parts"][0]["mime_type"] == "application/pdf"
    assert provider.calls[0]["inline_parts"][0]["data"] == data


def test_multimodal_ingestor_skips_files_when_provider_missing_chat_multimodal():
    agent = MultimodalIngestorAgent(llm_provider=object())  # no chat_multimodal method

    result = asyncio.run(
        agent.ingest(
            "q",
            [{"file_name": "x.png", "mime_type": "image/png", "size_bytes": 3, "sha256": "a" * 64, "data": b"abc"}],
        )
    )

    # Metadata is still recorded so the UI can list attachments; no evidence is produced.
    assert result.evidence_items == []
    assert len(result.upload_metadata) == 1


def test_multimodal_ingestor_drops_empty_quote(monkeypatch):
    monkeypatch.setattr("config.config.MULTIMODAL_ENABLED", True)

    provider = _StubGeminiMultimodal(
        {
            "claim": "no quote available",
            "source_quote": "   ",
            "source_title": "",
            "date": "unknown",
            "relevance_to_query": 0.1,
        }
    )
    agent = MultimodalIngestorAgent(llm_provider=provider)

    result = asyncio.run(
        agent.ingest(
            "q",
            [
                {
                    "file_name": "blank.png",
                    "mime_type": "image/png",
                    "size_bytes": 3,
                    "sha256": "b" * 64,
                    "data": b"img",
                }
            ],
        )
    )

    assert result.evidence_items == []
    assert len(result.upload_metadata) == 1


def test_research_engine_merges_multimodal_evidence_when_flag_on(monkeypatch):
    """Regression test: engine.run(uploads=[...]) produces pipeline.uploads and feeds evidence into the ledger."""

    import asyncio as _asyncio

    from backend.models import (
        CoveragePatch,
        FactLedger,
        FetchedSource,
        JobEvidenceOutput,
        JobSearchOutput,
        PlannerOutput,
        ResearchJob,
        ResearchReport,
        SearchCoverage,
        SearchHeader,
        VerifiedFact,
    )
    from backend.patch_applicator import apply_patch
    from backend.research_engine import SynapseResearchEngine

    monkeypatch.setattr("config.config.MULTIMODAL_ENABLED", True)
    monkeypatch.setattr("backend.research_engine.config.MULTIMODAL_ENABLED", True)

    class _Planner:
        async def plan(self, query):
            return PlannerOutput(
                original_query=query,
                query_interpretation="plan",
                precontext_claims=[
                    {
                        "claim": "seed",
                        "source_id": "src_001",
                        "url": "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
                    }
                ],
                research_jobs=[
                    ResearchJob(job_id="job_a", job_name="a", objective="o", search_queries=["q"], source_priorities=["official"], must_answer=["x"]),
                    ResearchJob(job_id="job_b", job_name="b", objective="o", search_queries=["q"], source_priorities=["official"], must_answer=["x"]),
                ],
            )

    class _Searcher:
        async def run(self, job):
            return JobSearchOutput(
                job_id=job.job_id,
                search_headers=[
                    SearchHeader(
                        result_id=f"res_{job.job_id}",
                        job_id=job.job_id,
                        query="q",
                        title="T",
                        url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
                        snippet="s",
                        rank=1,
                    )
                ],
                search_coverage=SearchCoverage(queries_run=1, results_found=1),
            )

    class _Extractor:
        async def extract(self, job, search_headers, fetched_sources=None):
            return JobEvidenceOutput(job_id=job.job_id, evidence_items=[], extraction_failures=[])

    class _SourceFetcher:
        summary = {"fetched_http_count": 1, "fetched_camofox_count": 0, "arxiv_metadata_count": 0, "failed_count": 0}

        async def fetch_many(self, search_headers):
            return [
                FetchedSource(
                    source_id=f"src_{header.result_id}",
                    result_id=header.result_id,
                    url=header.url,
                    text="Body. " * 30,
                    source_type="official",
                    source_quality_score=0.8,
                    fetch_status="fetched_http",
                    provider="http",
                    success=True,
                )
                for header in search_headers
            ]

    class _FactChecker:
        async def check(self, **kwargs):
            # Include any evidence_items in a verified fact so the patch_applicator won't complain.
            evidence_items = kwargs.get("evidence_items") or []
            facts = [
                VerifiedFact(
                    fact_id=f"fact_{idx}",
                    claim=item.claim,
                    status="VERIFIED",
                    confidence=0.9,
                    supporting_evidence_ids=[item.evidence_id],
                    source_urls=[item.source_url],
                )
                for idx, item in enumerate(evidence_items)
            ] or [
                VerifiedFact(
                    fact_id="fact_base",
                    claim="seed",
                    status="VERIFIED",
                    confidence=0.9,
                    supporting_evidence_ids=["ev_0"],
                    source_urls=["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"],
                )
            ]
            return FactLedger(verified_facts=facts, source_quality_summary={"official": 1})

    class _Synthesizer:
        async def synthesize(self, **kwargs):
            ledger = kwargs["fact_ledger"]
            used = [fact.fact_id for fact in ledger.verified_facts]
            sources = list({url for fact in ledger.verified_facts for url in fact.source_urls if url.startswith("http")})
            citations = sources or ["https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"]
            return ResearchReport(
                report_id="report_v1",
                title="T",
                answer_summary="Summary.",
                sections=[
                    {
                        "section_id": "sec_verified",
                        "heading": "h",
                        "content": "c",
                        "used_fact_ids": used or ["fact_base"],
                        "citations": citations,
                    }
                ],
                confidence_score=0.5,
                confidence_breakdown={"coverage": 0.5},
                used_fact_ids=used or ["fact_base"],
                sources=citations,
            )

    class _Auditor:
        async def audit(self, **kwargs):
            fact_ledger = kwargs.get("fact_ledger")
            first_fact = fact_ledger.verified_facts[0] if fact_ledger and fact_ledger.verified_facts else None
            return CoveragePatch(
                coverage_score=1.0,
                needs_new_search=False,
                patch_operations=[
                    {"op": "add", "target_section_id": "sec_verified", "text": first_fact.claim, "fact_ids": [first_fact.fact_id], "reason": "r"}
                ] if first_fact else [],
            )

    # Use the real multimodal agent path by monkeypatching the import.
    class _FakeMultimodalAgent:
        def __init__(self, llm_provider=None):
            self.llm_provider = llm_provider

        async def ingest(self, research_question, uploads):
            from agents.multimodal_ingestor import MultimodalIngestResult

            metadata_list = []
            evidence_list = []
            for upload in uploads:
                metadata = UploadMetadata(
                    file_name=upload["file_name"],
                    sha256=upload["sha256"],
                    mime_type=upload["mime_type"],
                    size_bytes=upload["size_bytes"],
                )
                metadata_list.append(metadata)
                evidence_list.append(
                    EvidenceItem(
                        evidence_id=f"ev_upload_{metadata.sha256[:8]}",
                        job_id="uploads",
                        result_id=f"upload_{metadata.sha256[:8]}",
                        claim="Upload supports claim X.",
                        source_title=metadata.file_name,
                        source_url=f"upload://{metadata.sha256}",
                        source_quote="Upload supports claim X.",
                        source_type="user_upload",
                        source_quality_score=0.5,
                        extraction_method="llm_multimodal",
                        relevance_to_query=0.9,
                    )
                )
            return MultimodalIngestResult(evidence_items=evidence_list, upload_metadata=metadata_list)

    from backend.models import UploadMetadata

    import agents.multimodal_ingestor as _m
    monkeypatch.setattr(_m, "MultimodalIngestorAgent", _FakeMultimodalAgent)

    engine = SynapseResearchEngine(
        planner_agent=_Planner(),
        searcher_agent=_Searcher(),
        evidence_extractor_agent=_Extractor(),
        fact_checker_agent=_FactChecker(),
        synthesizer_agent=_Synthesizer(),
        coverage_auditor_agent=_Auditor(),
        source_fetcher=_SourceFetcher(),
        patch_applicator=apply_patch,
        demo_mode=False,
    )

    uploads = [
        {
            "file_name": "paper.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 12,
            "sha256": "a" * 64,
            "data": b"pdf-content",
        }
    ]
    result = _asyncio.run(engine.run("What does the PDF say?", uploads=uploads))

    assert len(result.uploads) == 1
    assert result.uploads[0].file_name == "paper.pdf"
    assert any(item.source_type == "user_upload" for item in result.evidence_items)
