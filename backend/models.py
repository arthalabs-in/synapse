"""Pydantic data contracts for the SYNAPSE research pipeline."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.validators import require_source_quote, require_url


class SynapseModel(BaseModel):
    """Shared model config for strict, explicit pipeline contracts."""

    model_config = ConfigDict(extra="forbid")


class PrecontextClaim(SynapseModel):
    claim: str
    source_id: str
    url: str
    support_level: Literal["strong", "weak"] = "weak"

    @field_validator("url")
    @classmethod
    def _valid_url(cls, value: str) -> str:
        return require_url(value, "url")


class ResearchJob(SynapseModel):
    job_id: str
    job_name: str
    objective: str
    search_queries: list[str]
    source_priorities: list[str] = Field(default_factory=list)
    must_answer: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    evidence_requirements: dict[str, Any] = Field(
        default_factory=lambda: {
            "min_sources": 5,
            "require_quotes": True,
            "allow_snippet_only": False,
        }
    )


class CoverageRequirement(SynapseModel):
    requirement_id: str
    label: str
    description: str
    required_targets: list[str] = Field(default_factory=list)
    required_dimensions: list[str] = Field(default_factory=list)


class EvidenceCriteria(SynapseModel):
    comparison_targets: list[str] = Field(default_factory=list)
    decision_dimensions: list[str] = Field(default_factory=list)
    preferred_source_types: list[str] = Field(default_factory=list)
    avoid_source_patterns: list[str] = Field(default_factory=list)
    source_fitness_terms: list[str] = Field(default_factory=list)
    narrow_source_warnings: list[str] = Field(default_factory=list)
    coverage_requirements: list[CoverageRequirement] = Field(default_factory=list)


class GroundedChunk(SynapseModel):
    """Phase 3.1: a single citation chunk returned by Gemini Search grounding."""

    uri: str
    title: str = ""
    snippet: str = ""

    @field_validator("uri")
    @classmethod
    def _valid_uri(cls, value: str) -> str:
        return require_url(value, "uri")


class GroundedPrecontext(SynapseModel):
    """Phase 3.1: optional Gemini-native grounded precontext block."""

    summary: str
    supporting_chunks: list[GroundedChunk] = Field(default_factory=list)
    rendered_content: str | None = None


class PlannerPrecontext(SynapseModel):
    original_query: str
    query_type: str = "general"
    query_interpretation: str
    precontext_claims: list[PrecontextClaim]
    planning_risks: list[str] = Field(default_factory=list)
    research_jobs: list[ResearchJob]
    coverage_checklist: list[str] = Field(default_factory=list)
    evidence_criteria: EvidenceCriteria = Field(default_factory=EvidenceCriteria)
    planner_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # Phase 3.1: optional Gemini Search grounding precontext (additive; defaults to None).
    grounded_precontext: GroundedPrecontext | None = None


class SearchHeader(SynapseModel):
    result_id: str
    job_id: str = ""
    query: str
    title: str
    url: str
    snippet: str
    rank: int = Field(ge=1)
    provider: str = "unknown"
    source_type_guess: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)
    arxiv_id: str | None = None
    pdf_url: str | None = None
    published_date: str | None = None

    @field_validator("url")
    @classmethod
    def _valid_url(cls, value: str) -> str:
        return require_url(value, "url")

    @property
    def source(self) -> str:
        """Compatibility label for older code that expected a provider source."""
        return self.job_id


class SearchCoverage(SynapseModel):
    queries_run: int = 0
    results_found: int = 0
    official_sources_found: int = 0
    academic_sources_found: int = 0


class JobSearchOutput(SynapseModel):
    job_id: str
    search_headers: list[SearchHeader] = Field(default_factory=list)
    search_coverage: SearchCoverage = Field(default_factory=SearchCoverage)
    search_errors: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceItem(SynapseModel):
    evidence_id: str
    job_id: str
    result_id: str
    claim: str
    source_title: str
    source_url: str
    source_quote: str
    fetched_source_id: str | None = None
    quote_location: str = "snippet"
    source_type: str = "unknown"
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: str = "deterministic"
    fallback_reason: str | None = None
    date: str = "unknown"
    relevance_to_query: float = Field(default=0.0, ge=0.0, le=1.0)
    target: str = ""
    dimension: str = ""
    evidence_fit_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_fit_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("source_url")
    @classmethod
    def _valid_source_url(cls, value: str) -> str:
        return require_url(value, "source_url")

    @field_validator("source_quote")
    @classmethod
    def _valid_source_quote(cls, value: str) -> str:
        return require_source_quote(value, "source_quote")


class ExtractionFailure(SynapseModel):
    result_id: str
    reason: str


class JobEvidenceOutput(SynapseModel):
    job_id: str
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    extraction_failures: list[ExtractionFailure] = Field(default_factory=list)


class VerifiedFact(SynapseModel):
    fact_id: str
    claim: str
    status: Literal["VERIFIED", "PARTIAL", "UNSUPPORTED", "CONTRADICTED"]
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    notes: str = ""
    verification_method: str = "heuristic_fallback"

    @field_validator("source_urls")
    @classmethod
    def _valid_source_urls(cls, values: list[str]) -> list[str]:
        return [require_url(value, "source_urls") for value in values]


class Contradiction(SynapseModel):
    cluster_id: str
    topic: str
    side_a_claim: str
    side_a_evidence_ids: list[str] = Field(default_factory=list)
    side_b_claim: str
    side_b_evidence_ids: list[str] = Field(default_factory=list)
    resolution: Literal["unresolved", "stronger_a", "stronger_b", "context_dependent"]


class FactLedger(SynapseModel):
    verified_facts: list[VerifiedFact] = Field(default_factory=list)
    partial_facts: list[VerifiedFact] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    unsupported_claims: list[dict[str, Any]] = Field(default_factory=list)
    dropped_evidence: list[dict[str, Any]] = Field(default_factory=list)
    source_quality: dict[str, int] = Field(
        default_factory=lambda: {
            "official": 4,
            "academic": 3,
            "news": 2,
            "blog": 1,
            "unknown": 0,
        }
    )
    source_quality_summary: dict[str, int] = Field(default_factory=dict)
    summary: str = ""


class FetchedSource(SynapseModel):
    source_id: str
    result_id: str
    url: str
    canonical_url: str | None = None
    title: str | None = None
    domain: str | None = None
    text: str = ""
    markdown: str | None = None
    source_type: str = "unknown"
    source_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    provider: str = "unknown"
    fetch_status: Literal[
        "fetched_http",
        "fetched_camofox",
        "arxiv_metadata_only",
        "failed",
        "skipped",
    ] = "failed"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def _valid_url(cls, value: str) -> str:
        return require_url(value, "url")


class LLMUsage(SynapseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(SynapseModel):
    text: str
    parsed_json: dict[str, Any] | None = None
    model: str
    provider: str
    usage: LLMUsage | None = None
    latency_ms: float | None = None
    raw_response: dict[str, Any] | None = None


class ReportSection(SynapseModel):
    section_id: str
    heading: str
    content: str
    used_fact_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)

    @field_validator("citations")
    @classmethod
    def _valid_citations(cls, values: list[str]) -> list[str]:
        return [require_url(value, "citations") for value in values]


class KeyFinding(SynapseModel):
    finding: str
    fact_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("citations")
    @classmethod
    def _valid_citations(cls, values: list[str]) -> list[str]:
        return [require_url(value, "citations") for value in values]


class ResearchReport(SynapseModel):
    report_id: str = "report_v1"
    title: str
    answer_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    key_findings: list[KeyFinding] = Field(default_factory=list)
    contradictions_or_uncertainties: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_not_included: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_breakdown: dict[str, float] = Field(default_factory=dict)
    used_fact_ids: list[str] = Field(default_factory=list)
    unused_fact_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    iterations: int = 1
    patch_applied: bool = False
    degraded_synthesis: bool = False

    @field_validator("sources")
    @classmethod
    def _valid_sources(cls, values: list[str]) -> list[str]:
        return [require_url(value, "sources") for value in values]

    @model_validator(mode="after")
    def _requires_citations_for_claims(self):
        for section in self.sections:
            if section.content and section.used_fact_ids and not section.citations:
                raise ValueError(f"section {section.section_id} must include citations")
        for finding in self.key_findings:
            if finding.finding and finding.fact_ids and not finding.citations:
                raise ValueError("key findings with fact_ids must include citations")
        return self


class PatchOperation(SynapseModel):
    edit_id: str | None = None
    op: Literal["add", "replace", "remove", "remove_unsupported", "weaken", "add_caveat"]
    target_section_id: str | None = None
    target_path: str | None = None
    edit_label: str | None = None
    original_text: str | None = None
    replacement_text: str | None = None
    text: str
    fact_ids: list[str] = Field(default_factory=list)
    contradiction_ids: list[str] = Field(default_factory=list)
    result_ids: list[str] = Field(default_factory=list)
    reason: str

    @model_validator(mode="after")
    def _requires_reference(self):
        if not self.fact_ids and not self.contradiction_ids and not self.result_ids:
            raise ValueError("patch operation must reference fact_ids, contradiction_ids, or result_ids")
        return self


class CoverageDiff(SynapseModel):
    missed_verified_details: list[dict[str, Any]] = Field(default_factory=list)
    missed_caveats: list[dict[str, Any]] = Field(default_factory=list)
    missed_contradictions: list[dict[str, Any]] = Field(default_factory=list)
    search_result_unused_but_relevant: list[dict[str, Any]] = Field(default_factory=list)
    missing_user_intent: list[dict[str, Any]] = Field(default_factory=list)
    revision_brief: dict[str, Any] = Field(default_factory=dict)


class CoveragePatch(SynapseModel):
    coverage_score: float = Field(ge=0.0, le=1.0)
    coverage_diff: CoverageDiff = Field(default_factory=CoverageDiff)
    missed_verified_details: list[dict[str, Any]] = Field(default_factory=list)
    missed_caveats: list[dict[str, Any]] = Field(default_factory=list)
    missed_contradictions: list[dict[str, Any]] = Field(default_factory=list)
    search_results_unused_but_relevant: list[dict[str, Any]] = Field(default_factory=list)
    missing_user_intent: list[dict[str, Any]] = Field(default_factory=list)
    revision_brief: dict[str, Any] = Field(default_factory=dict)
    patch_operations: list[PatchOperation] = Field(default_factory=list)
    needs_new_search: bool = False
    followup_research_jobs: list[ResearchJob] = Field(default_factory=list)


class UploadMetadata(SynapseModel):
    """Phase 3.2: metadata block summarizing a user-uploaded file for the pipeline."""

    file_name: str
    sha256: str
    mime_type: str
    size_bytes: int


class PipelineResult(SynapseModel):
    research_question: str
    planner_precontext: PlannerPrecontext
    search_headers: list[SearchHeader] = Field(default_factory=list)
    fetched_sources: list[FetchedSource] = Field(default_factory=list)
    fetched_source_summary: dict[str, int] = Field(default_factory=dict)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    fact_ledger: FactLedger
    report: ResearchReport
    report_v1: ResearchReport | None = None
    report_v2: ResearchReport | None = None
    coverage_patch: CoveragePatch
    job_summaries: list[dict[str, Any]] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    provider_metrics: dict[str, Any] = Field(default_factory=dict)
    run_quality: dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False
    degraded_mode: bool = False
    errors: list[dict[str, Any]] = Field(default_factory=list)
    iterations: int = 1
    history: list[dict[str, Any]] = Field(default_factory=list)
    # Phase 3.2: additive field for user-supplied multimodal inputs (defaults to empty).
    uploads: list[UploadMetadata] = Field(default_factory=list)


class PatchApplicationResult(SynapseModel):
    report_v1: ResearchReport
    report_v2: ResearchReport
    applied_operations: list[PatchOperation] = Field(default_factory=list)


# Backward-compatible names used by the current skeleton.
PrecontextItem = PrecontextClaim
PlannerOutput = PlannerPrecontext
ReportV1 = ResearchReport
PatchPlan = CoveragePatch
FinalReport = ResearchReport
