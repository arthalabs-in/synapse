# SYNAPSE

SYNAPSE is a research pipeline that keeps the evidence trail attached to the
answer. It searches public sources, fetches page text, extracts quoted
passages, checks claims against those passages, and records the edits made
during a final coverage pass.

The working rule is simple: a search result is not evidence. A claim can enter
the report only after the corresponding source text has been fetched and the
supporting passage has been preserved.

## Pipeline

```text
question
  -> planner
  -> search jobs
  -> source fetch and cleanup
  -> quote extraction
  -> fact ledger
  -> report draft
  -> coverage audit
  -> constrained patch
  -> final artifact
```

The main contracts are Pydantic models in `backend/models.py`:

- `SearchHeader` describes a candidate result.
- `FetchedSource` stores retrieved text and fetch status.
- `EvidenceItem` binds a claim to a URL and source quote.
- `FactLedger` separates verified, partial, unsupported, and contradicted claims.
- `ResearchReport` stores cited sections and findings.
- `CoveragePatch` records bounded edits and their references.
- `PipelineResult` contains the complete run, timings, errors, and provider data.

See [ARCHITECTURE.md](ARCHITECTURE.md) for stage responsibilities and provider
boundaries.

## Run locally

Python 3.10 or newer is required.

```bash
pip install -r requirements.txt
python -m pytest
streamlit run frontend/app.py
```

Copy `.env.example` to `.env` for live runs. The default LLM provider is
Gemini, but provider construction is centralized in
`backend/providers/llm/factory.py`.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-pro
```

## Demo mode

Demo mode loads a checked fixture and makes no network or model calls:

```env
DEMO_MODE=true
GOLDEN_RESULT_PATH=tests/fixtures/demo_golden.json
```

The fixture is useful for UI review and deployment smoke tests. It is not a
substitute for a live run.

## Live artifact check

```bash
python scripts/run_live_golden.py \
  --query "What are the strongest evidence-backed approaches for building a trustworthy research assistant?" \
  --out artifacts/live_golden_run.json \
  --trace artifacts/live_golden_trace.md \
  --timeout 900

python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

The validator checks artifact consistency: real-looking public URLs, fetched
sources, quoted evidence, fact references, patch references, provider metrics,
and recorded fallback or truncation signals. It does not independently prove
that a claim is true. The report remains inspectable because the source quote
and status are retained.

## Repository layout

```text
agents/             planner, search, extraction, checking, synthesis, audit
backend/            contracts, orchestration, validators, provider interfaces
backend/providers/  LLM, search, browser, source, and reranking adapters
frontend/           Streamlit workbench and theme
scripts/            live-run and artifact-audit utilities
tests/              deterministic unit and integration tests
docs/               architecture and provider notes
submission/         deployment and Horizons readiness notes
```

## Current limitations

- Live quality depends on public source availability and provider output.
- A preserved quote can still be ambiguous, outdated, or misinterpreted.
- Deterministic fallbacks are deliberately marked as degraded evidence.
- Camofox is optional and only handles public pages where normal HTTP fetching
  returns unusable text.
- Semantic reranking, multimodal ingestion, grounded precontext, and the live
  tool agent are feature-flagged.

Do not commit `.env`, provider keys, private source material, or generated run
artifacts that contain sensitive data.
