# What I Did

This document records the repo changes made during the Gemini hackathon pivot and the live-run debugging pass.

## Gemini-First Provider Direction

- Changed the project direction from the AMD/H100 golden question toward the Milan AI Week Gemini track.
- Made Gemini the default first-class provider in configuration.
- Kept OpenCode Go as a temporary modular provider so we can keep testing with the user's existing API key while Gemini credentials are being finalized.
- Removed the older vLLM provider path from the active provider factory.
- Added Gemini/OpenCode Go environment knobs in `config.py` and `.env.example`.
- Added `docs/GEMINI_HACKATHON_BRIEF.md` for the hackathon positioning.

## Live LLM Debugging

- Confirmed that OpenCode Go with `deepseek-v4-flash` can return normal visible text on a tiny smoke prompt.
- Confirmed the full SYNAPSE live run was hitting the model API: provider metrics showed planner, extraction, fact-check, and synthesis calls.
- Found the real blocker: final synthesis calls could return HTTP 200 with token usage but empty visible `message.content`.
- Confirmed that the old validator could still pass in that state because deterministic fallback sections had real URLs, fact IDs, and citations.

## Provider Hardening

- Hardened `backend/providers/llm/openai_compatible.py`.
- Added `EmptyVisibleContentError` for the exact failure mode where a provider spends tokens but returns no visible assistant text.
- Added robust content extraction for plain string content and list-of-text-parts content.
- Added reasoning-aware telemetry:
  - `finish_reason`
  - `reasoning_tokens`
  - `visible_chars`
  - `reasoning_content_chars`
  - `truncated_by_reasoning`
- Added passthrough support for `reasoning_effort` and `reasoning` request kwargs.
- Extended `LLMUsage` with `reasoning_tokens`.

## Synthesizer Changes

- Wired the research engine so `SynthesizerAgent` receives an LLM provider instead of always using deterministic report assembly.
- Added per-stage synthesizer provider config:
  - `SYNTHESIZER_PROVIDER`
  - `SYNTHESIZER_MODEL`
  - `SYNTHESIZER_MAX_TOKENS`
- `SYNTHESIZER_REASONING_EFFORT`
- `SYNTHESIZER_TEMPERATURE`
- After live diagnosis, set the synthesizer defaults to `SYNTHESIZER_MAX_TOKENS=64000` and `SYNTHESIZER_REASONING_EFFORT=high` because OpenCode Go / DeepSeek rejects `minimal`, and smaller visible-output budgets were consumed entirely by hidden reasoning tokens.
- Reworked the synthesis prompt to be shorter, more literal, and citation-oriented.
- Added inline fact ID parsing from sections, so a section citing `[fact_001]` only receives that fact's citations instead of every fact in the report.
- Added `SynthesisDegradedError` so live synthesis failures do not silently masquerade as successful model-written reports.
- Kept deterministic synthesis available for no-provider/demo/library mode.
- In the engine, explicit synthesis degradation now records an error and sets `degraded=True` before using fallback.
- Added `degraded_synthesis` to `ResearchReport`.

## Validator Tightening

- Updated `scripts/validate_live_golden.py` to catch the exact bad state we observed.
- The validator now fails if:
  - a synthesis text call returns empty visible content without an explicit synthesizer error;
  - a successful text synthesis call exists but all report sections are deterministic IDs such as `sec_verified`;
  - the summary appears to be deterministic concatenated fact claims.

## Search And Evidence Quality

- Added a source cleaner around fetched text using the existing Trafilatura path plus SYNAPSE-specific filters for curl/API-key/docs navigation/login boilerplate.
- Added per-source async LLM extraction with configurable extraction budget and concurrency:
  - `EXTRACTION_MAX_TOKENS`
  - `EXTRACTION_REASONING_EFFORT`
  - `EXTRACTION_MAX_CONCURRENT_CALLS`
- Added normalized/fuzzy quote anchoring so LLM-selected quotes can be accepted when whitespace differs from fetched text.
- Added evidence quality gates so unrelated, robotics-specific, non-Gemini-specific, or boilerplate/code evidence does not become supported facts.
- Isolated DuckDuckGo search in a subprocess to avoid stuck worker shutdowns.
- Reduced arXiv bottlenecks with async HTTP XML parsing and timeouts.
- Added quote cleanup to avoid obvious navigation/header boilerplate.
- Rejected PDF/binary-looking source text instead of treating it as usable evidence.
- Added fallback quote caps so huge scraped sentences do not become giant claims.
- Balanced fetched-source selection across research jobs so one job does not starve the other after global reranking.
- Deduped evidence in fact checking when the same items arrive through multiple paths.

## Test Status

Current local deterministic test suite:

```text
100 passed
```

Important new tests cover:

- empty visible content from OpenAI-compatible providers;
- list-of-parts message content extraction;
- reasoning token telemetry;
- reasoning kwargs passthrough;
- provider-backed synthesis;
- no silent fallback on synthesis failure;
- retry behavior for empty synthesis text;
- per-section inline fact attribution;
- engine-level explicit degraded synthesis handling;
- validator rejection of the previous silent fallback failure mode.

## Current Honest Status

The code is now stricter and safer. The old Milan Gemini artifact passed the old validator, but it was not a good demo artifact because synthesis fell back to deterministic text after empty visible model output.

With the new validator and provider checks, that exact failure mode should be surfaced instead of hidden. The next live run should be judged by the stricter rules: it must contain `sec_llm_` report sections and visible synthesis text from the model, or it must fail/degrade explicitly.
