# Submission Answers

Use this as paste-ready submission copy. Replace bracketed items only after you
have the final demo URL, video URL, team name, and GitHub URL.

## Project Name

SYNAPSE

## Tagline

Answers you can audit.

## Short Description

SYNAPSE is an AI research workbench that turns hard questions into auditable
answers. It searches public sources, fetches source text, extracts direct
quotes, verifies claims into a fact ledger, blocks unsupported statements, and
shows exactly how the final answer was patched.

## Theme Fit

Primary theme: Artificial Intelligence & Machine Learning

Secondary themes: Education Technology, Startup & Productivity Solutions, Open
Innovation

## Inspiration

Most AI research tools produce confident prose faster than people can verify it.
That is dangerous for students, nonprofits, researchers, founders, and small
teams that need trustworthy reports but do not have time to manually audit every
claim. SYNAPSE was built around a simple question: what if an AI answer had to
show its evidence chain before we trusted it?

## What It Does

SYNAPSE takes a research question and runs it through an evidence-first
pipeline:

1. Plans the question into focused research jobs.
2. Searches public sources and fetches readable source text.
3. Extracts evidence only when it can attach a direct source quote.
4. Builds a fact ledger of verified, partial, unsupported, and contradictory
   claims.
5. Synthesizes a cited answer from the ledger.
6. Audits the answer against the original question, evidence, and unsupported
   claims.
7. Applies visible patch operations that include the edit reason, location,
   before text, and replacement text.
8. Displays the result in a research workbench with source cards, evidence,
   fact ledger, validator, patch diff, provider telemetry, and run history.

## Why It Matters

AI is increasingly used for grant writing, policy research, product decisions,
technical comparisons, education support, and nonprofit operations. In those
settings, a fluent answer is not enough. People need to know which claims are
supported, which are weak, and which were removed. SYNAPSE helps users get the
speed of AI without giving up auditability.

## How We Built It

SYNAPSE is a Python multi-agent research pipeline with a Streamlit workbench UI.
The backend uses explicit Pydantic contracts between stages so each agent has a
clear responsibility:

- Planner: turns the user question into research jobs and coverage targets.
- Searcher: finds candidate public sources.
- Source fetcher: fetches, cleans, normalizes, and scores source text.
- Evidence extractor: extracts quote-grounded evidence items.
- Fact checker: reconciles evidence into a fact ledger.
- Synthesizer: writes the answer using fact IDs.
- Coverage auditor: checks missing coverage and unsupported claims.
- Patch applicator: rewrites the answer with explicit edit metadata.
- Validator: rejects fake URLs, missing quotes, unsupported claims, silent
  fallback, and malformed patch operations.

The frontend shows the pipeline as it runs, including live stage status,
evidence cards, source cards, fact ledger, validation signals, patch diff, and a
history tab for previous prompts and answers.

## Technical Highlights

- Provider-first architecture for search, source fetching, LLMs, and reranking.
- Async research jobs and source extraction.
- Direct source quote requirements for evidence.
- Fact ledger with verified, partial, unsupported, and contradiction records.
- UI-ready patch diff schema with edit reason, location, before, and after.
- Live pipeline progress events from backend to frontend.
- Run quality and provider telemetry.
- Deterministic validator for live golden artifacts.
- Demo mode for reliable judging when network or API access is unstable.
- 168 passing tests at the time of submission.

## What Makes It Different

Many hackathon AI projects stop at a final answer. SYNAPSE makes the final
answer only one part of the product. The product is the audit trail: sources,
quotes, evidence IDs, fact IDs, validator checks, patch reasons, and run
quality. This makes it useful for real-world knowledge work where trust matters.

## Challenges We Ran Into

The hardest challenge was preventing silent degradation. Some reasoning models
can spend their token budget internally and return little or no visible content.
SYNAPSE now records provider telemetry, detects empty visible responses, exposes
fallback reasons, and validates that the final artifact was not silently built
from deterministic fallback when a live model call failed.

We also had to keep the UI honest. A normal blocking pipeline made the interface
look stuck during long model calls. We added backend progress events and a
frontend worker-thread progress bridge so users can see the current stage while
research is running.

## Accomplishments

- Built a full evidence-first research pipeline, not just a chatbot wrapper.
- Added a polished workbench UI for running and auditing research.
- Implemented live progress tracking for each pipeline stage.
- Added run history so previous prompts and answers can be inspected.
- Added quote-grounding, fact ledger, patch diff, provider telemetry, and
  validator checks.
- Kept the project testable with a deterministic unit suite.

## What We Learned

The biggest lesson is that trustworthy AI is mostly about workflow design. A
better model helps, but the system must still preserve sources, quotes,
intermediate claims, validation, and correction metadata. Without those layers,
users are forced to trust prose instead of inspecting evidence.

## What's Next

- Deploy a hosted public demo.
- Add source-side highlighting so clicking a fact opens the exact quoted text.
- Add collaborative review and exportable reports for teams.
- Add project folders for schools, nonprofits, founders, and research groups.
- Add stronger source credibility scoring and domain-specific validators.
- Add a reviewer mode that lets humans approve, reject, or request more
  evidence for each claim.

## Technologies Used

- Python
- Streamlit
- Pydantic
- asyncio
- HTTPX
- DuckDuckGo/DDGS search
- arXiv search
- Gemini-compatible provider interfaces
- OpenAI-compatible / OpenCode Go-compatible LLM provider path
- Source cleaning and quality scoring
- pytest

## Links

- GitHub Repository: [add URL]
- Demo Link: [add URL]
- Walkthrough Video: [add URL]

