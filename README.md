# SYNAPSE

SYNAPSE is an evidence-first AI research agent for trustworthy knowledge work.
It turns a hard question into a traceable chain of searched sources, fetched
text, quote-grounded evidence, verified facts, unsupported-claim checks, a
cited answer, and a patch diff that explains what changed and why.

Tagline: **Answers you can audit.**

## Why It Exists

Most AI research tools produce fluent summaries with decorative links. SYNAPSE
is built around the opposite contract: every final claim must be traceable to a
source quote and a fact ID, and any unsupported claim must be rejected, caveated,
or patched before the final report is accepted.

This makes SYNAPSE useful for students, researchers, builders, analysts, and
teams who need AI help without losing the ability to verify where an answer came
from.

## Architecture

```text
query
  -> Planner
  -> 2 async ResearchJobs
      -> Searcher
      -> SourceFetcher
      -> EvidenceExtractor
  -> FactChecker
  -> Synthesizer(report_v1)
  -> CoverageAuditor
  -> PatchApplicator(report_v2)
  -> Validator / Run Quality
```

Provider interfaces live under `backend/providers/`:

- `search/`: DuckDuckGo/DDGS, arXiv, and composite search providers.
- `browser/`: HTTP fetcher and optional Camofox REST browser fallback.
- `sources/`: normalization, cleaning, source quality scoring, and fetching.
- `llm/`: Gemini-first provider plus a modular OpenCode Go compatibility path.

Agents depend on provider interfaces, not provider-specific implementations.

## Core Capabilities

- Quote-grounded evidence extraction from fetched source text.
- Fact ledger with `VERIFIED`, `PARTIAL`, `UNSUPPORTED`, and contradiction records.
- Pydantic schemas between every major pipeline stage.
- Coverage auditor that compares the final answer against the original question,
  evidence, fact ledger, and unsupported claims.
- UI-ready patch operations with edit ID, location, reason, before text, and
  replacement text.
- Live golden validator that fails on fake URLs, missing quotes, unsupported
  claims, ungrounded patch operations, and missing provider metrics.
- Demo mode for reliable judging when live APIs or Wi-Fi are unstable.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Run tests:

```bash
python -m pytest
```

Run the Streamlit UI:

```bash
streamlit run frontend/app.py
```

## Live Mode

Live mode needs public web access, source fetching, and an LLM provider key.
The default provider is Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_MODEL=gemini-2.5-pro
```

SYNAPSE uses structured JSON calls for planning, extraction, fact checking, and
coverage auditing. It records provider metrics, reasoning-token telemetry where
available, stage timing, and run quality.

## Live Golden Trace

Run a real trace:

```bash
python scripts/run_live_golden.py --query "What are the strongest evidence-backed approaches for building a trustworthy AI research assistant for students and builders?" --out artifacts/live_golden_run.json --trace artifacts/live_golden_trace.md --timeout 900
```

Validate that the result is real and grounded:

```bash
python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

The validator fails on fake/local URLs, missing fetched sources, missing source
quotes, missing fact IDs, unsupported claims leaking into the report, patch ops
without valid references, silent LLM fallback, and absent provider metrics.

## Demo Mode

Demo mode loads a validated fixture and requires no internet or LLM server. It
is the safest path for UI inspection and judging:

```env
DEMO_MODE=true
GOLDEN_RESULT_PATH=tests/fixtures/demo_golden.json
```

## Documentation

- `ARCHITECTURE.md`: system architecture and stage contracts.
- `VERIFICATION_FRAMEWORK.md`: validator, run quality, and trust guarantees.
- `docs/ARCHITECTURE_OVERVIEW.md`: judge-friendly architecture overview.
- `docs/PROJECT_CHARTER.md`: submission-facing project positioning.
- `submission/`: Horizons submission pack, deploy notes, and pitch copy.

## Submission Pack

For hackathon or program judging, start here:

- `submission/horizons/README.md`: how Horizons qualification works + SYNAPSE-specific rules.
- `submission/horizons/ship_checklist.md`: pre-ship readiness checklist.
- `submission/DEPLOY.md`: public demo deployment notes.
- `docs/ARCHITECTURE_OVERVIEW.md`: simple architecture diagram and stage contracts.

Best one-line pitch:

> SYNAPSE is an AI research workbench that gives you answers you can audit:
> every important claim links back to source quotes, weak claims are blocked,
> and edits are explained.

## Safety

Do not commit `.env` or API keys. Treat search results, fetched pages, and model
outputs as untrusted input until they pass quote, URL, fact ID, and validator
checks.
