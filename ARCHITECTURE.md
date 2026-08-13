# Architecture

SYNAPSE passes structured objects between narrow stages. Agents own research
decisions; providers own network and model access; the engine owns sequencing,
limits, timing, and failure reporting.

## Stage contracts

| Stage | Input | Output | Constraint |
| --- | --- | --- | --- |
| Planner | question | `PlannerPrecontext` | emits focused jobs and coverage targets |
| Searcher | `ResearchJob` | `SearchHeader` values | headers are candidates, not evidence |
| Fetcher | search headers | `FetchedSource` values | records fetch status and cleaned text |
| Extractor | fetched text | `EvidenceItem` values | every accepted item retains a source quote |
| Fact checker | evidence | `FactLedger` | classifies support and contradictions |
| Synthesizer | ledger | `ResearchReport` | cites ledger fact IDs |
| Coverage auditor | report, ledger, evidence | `CoveragePatch` | identifies gaps and bounded edits |
| Patch applicator | report and patch | final `ResearchReport` | rejects unsupported patch references |
| Engine | all stage output | `PipelineResult` | records timings, metrics, quality, and errors |

## Orchestration

`backend/research_engine.py` builds provider-backed agents and runs the pipeline.
Search and evidence work fan out asynchronously. Global caps limit candidate
headers, fetched sources, context length, and concurrent model calls.

The default run performs one research pass. `MAX_RESEARCH_ITERATIONS` can enable
additional gap-filling passes. Failures are attached to the result rather than
hidden behind a successful-looking report.

## Provider boundary

Provider implementations live under `backend/providers/`:

- `search/`: DuckDuckGo, arXiv, and composite search
- `browser/`: normal HTTP fetch and optional Camofox fallback
- `sources/`: normalization, cleanup, quality scoring, and source fetching
- `llm/`: Gemini and OpenAI-compatible providers
- `rerankers/`: optional FlashRank semantic reranking

Agents should receive provider objects or use the central factory. They should
not import a concrete network client directly.

## Evidence path

```text
SearchHeader
    candidate URL and snippet
        |
FetchedSource
    retrieved text, status, source quality
        |
EvidenceItem
    claim, exact quote, URL, fit and limitations
        |
VerifiedFact
    status, confidence, supporting evidence IDs
        |
ResearchReport
    section text, fact IDs, citations
```

Snippet-only evidence is a low-confidence fallback and must carry its
limitation. It cannot silently become a verified fact.

## Patch safety

A patch operation identifies its target, reason, previous text, replacement,
and supporting fact, contradiction, or result IDs. `backend/patch_applicator.py`
validates those references before editing the report. Synthesis and patching do
not introduce new evidence.

## Optional paths

- Gemini Search grounding can add planning precontext.
- Uploaded files can enter through the multimodal ingestor.
- FlashRank can contribute a semantic score during search reranking.
- The live tool agent can answer follow-up questions against a completed run.

All are gated by configuration and default to behavior that keeps deterministic
tests offline.

## Observability

`PipelineResult` stores wall-clock timing, stage timing, search/fetch events,
model usage, visible output counts, fallback reasons, truncation flags, and a
run-quality summary. These fields explain how a run degraded; they are not a
truth score.
