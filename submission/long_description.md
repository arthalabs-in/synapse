# Project explanation notes

Use these as prompts when writing the Horizons description in your own words.

## Problem observed

- Research answers often include links without retaining the passage used for a
  specific claim.
- Search snippets can be mistaken for verified evidence.
- Later revisions make it hard to see why the final wording changed.

## What was built

- a planner that creates bounded research jobs
- public web and arXiv search providers
- source fetching, cleanup, normalization, and quality scoring
- extraction that stores a claim beside its source quote
- a fact ledger with support status and contradictions
- report synthesis restricted to ledger facts
- a coverage audit and referenced patch format
- a Streamlit workbench and exported run artifact

## Implementation details worth explaining

- Python, Streamlit, Pydantic, `httpx`, Gemini/OpenAI-compatible provider boundary
- asynchronous search and evidence work
- deterministic tests that do not require live endpoints
- demo mode for stable UI review
- live validation for URLs, quotes, IDs, patches, provider metrics, and fallback signals

## Limits to state plainly

- validation checks consistency, not factual truth
- live runs depend on source and provider availability
- quote extraction can still misunderstand context
- demo mode uses a fixture

Do not paste this file into the submission form. Write a short account of what
you built, what you changed during the logged hours, and what remains imperfect.
