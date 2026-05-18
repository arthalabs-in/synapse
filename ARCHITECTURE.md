# SYNAPSE Architecture

SYNAPSE is an evidence-first AI research pipeline. Its purpose is not to make a
model sound confident; its purpose is to make each answer auditable.

## Design Principles

1. **Provider-first boundaries**: agents call provider interfaces, not concrete
   DuckDuckGo, Gemini, arXiv, browser, or fetch implementations.
2. **Quote before claim**: evidence extraction must preserve the source quote
   that supports a claim.
3. **Ledger before prose**: synthesis uses verified and partial facts from the
   fact ledger, not raw snippets or free-form search results.
4. **Patch instead of overwrite**: coverage auditing emits constrained patch
   operations with IDs, reasons, locations, and references.
5. **Live failures are honest**: degraded stages are recorded in errors,
   provider metrics, and run quality instead of being hidden.

## Pipeline

```text
User query
  -> Planner
      -> PlannerPrecontext
      -> 2 ResearchJob objects
  -> Searcher
      -> SearchHeader objects
  -> SourceFetcher
      -> FetchedSource objects
  -> EvidenceExtractor
      -> EvidenceItem objects with source_quote
  -> FactChecker
      -> FactLedger
  -> Synthesizer
      -> report_v1
  -> CoverageAuditor
      -> CoveragePatch and revision brief
  -> PatchApplicator
      -> report_v2
  -> Validator / Run Quality
```

## Core Data Contracts

- `SearchHeader`: a search result. It is not evidence.
- `FetchedSource`: fetched source text plus status, quality, and metadata.
- `EvidenceItem`: a claim anchored to a source quote and URL.
- `VerifiedFact`: a fact ledger entry classified as verified, partial,
  unsupported, or contradicted.
- `ResearchReport`: cited answer sections and key findings.
- `PatchOperation`: a constrained edit with operation, location, references,
  reason, before text, and replacement text.
- `PipelineResult`: full run artifact with timings, provider metrics, quality,
  reports, facts, evidence, and errors.

## Agents

- `PlannerAgent`: interprets the query and emits two research jobs.
- `SearcherAgent`: runs provider-aware search across web and arXiv.
- `EvidenceExtractorAgent`: extracts quote-grounded evidence from fetched
  sources, with deterministic fallback reasons when LLM extraction fails.
- `FactCheckerAgent`: batches entailment checks and creates the fact ledger.
- `SynthesizerAgent`: writes a cited report using only ledger facts.
- `CoverageAuditorAgent`: compares the report against user intent, evidence,
  unsupported claims, contradictions, and run quality.
- `PatchApplicator`: applies validated patch operations to produce `report_v2`.

## Providers

Provider modules live under `backend/providers/`:

- `llm/`: Gemini provider and OpenAI-compatible compatibility provider.
- `search/`: DuckDuckGo, arXiv, and composite search.
- `browser/`: HTTP fetcher and optional Camofox browser fallback.
- `sources/`: URL normalization, source cleaning, source quality, fetching.
- `rerankers/`: semantic reranking support.

## Observability

Every run records:

- stage timings
- wall-clock start/end
- search and fetch events
- LLM call logs
- visible response characters
- token usage where available
- reasoning-token telemetry where available
- truncation flags
- fallback reasons
- run quality signals

## Scalability

The current architecture is intentionally simple and production-friendly:

- async fan-out for search and extraction
- source and header caps to control cost
- per-stage model configuration
- bounded context selection before LLM calls
- deterministic fallbacks that preserve source quotes
- demo mode for repeatable presentation

Future scaling work can move provider calls to a queue, persist `PipelineResult`
artifacts to object storage, and split long research runs into resumable jobs.
