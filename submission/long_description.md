# SYNAPSE - Long Description

## Problem

Most AI research assistants sound confident even when their citations are weak,
missing, or unrelated. They may provide links, but they usually do not preserve
the exact source sentence behind each claim. This makes them risky for students,
builders, researchers, and decision-makers who need to trust the answer, not
just read fluent prose.

## Solution

SYNAPSE is an **evidence-first AI research agent**. It does not just summarize.
It builds an auditable trail from question to answer:

1. **Planner** interprets the question and creates focused research jobs.
2. **Searcher + SourceFetcher** collect and fetch real public sources.
3. **EvidenceExtractor** turns source text into quote-grounded evidence items.
4. **FactChecker** classifies claims as verified, partial, unsupported, or
   contradicted.
5. **Synthesizer** writes a cited answer using fact IDs from the ledger.
6. **CoverageAuditor** checks the answer against the original question, unused
   evidence, unsupported claims, contradictions, and run quality.
7. **PatchApplicator** produces a final answer with visible edit reasons,
   locations, before text, and replacement text.

Every major object is Pydantic-validated, and every live run can be checked by
`scripts/validate_live_golden.py`.

## Impact

SYNAPSE helps people use AI for research without blindly trusting it. Students
can verify where a statement came from. Builders can compare technical options
with source-backed tradeoffs. Teams can inspect unsupported claims before they
reach a final report.

## Technical Implementation

The system is an async Python pipeline with provider-first boundaries for LLMs,
search, source fetching, browser fallback, source quality, and reranking. The
default live stack uses Gemini 2.5 Pro and Gemini 2.5 Flash, but the architecture
is not hard-wired to one provider.

Key technical features:

- quote-grounded evidence extraction
- fact ledger with unsupported and contradiction tracking
- semantic source reranking
- source cleaning and quality scoring
- structured LLM outputs
- provider metrics and reasoning-token telemetry
- UI-ready patch diff metadata
- deterministic demo mode
- live golden validator

## Originality

Most hackathon AI demos show a final answer. SYNAPSE shows the audit trail:
source quote, URL, evidence ID, fact ID, verification status, report citation,
patch operation, and validator result. The system is built around the idea that
AI research should be inspectable, not just impressive.

## Demo

The demo shows a hard research question moving through the full pipeline:
planning, source search, source fetch, evidence extraction, fact checking,
synthesis, coverage audit, patch diff, and validation. The final proof is a
validator pass showing the artifact is real, grounded, and non-synthetic.
