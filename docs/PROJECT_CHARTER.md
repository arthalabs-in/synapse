# SYNAPSE Project Charter

## One-Line Pitch

SYNAPSE is an AI research agent that turns every answer into an auditable chain
of sources, quotes, fact IDs, validator checks, and patch decisions.

## Problem

AI assistants are useful, but they often collapse research into fluent prose
without preserving the evidence trail. Links may be present, but the specific
sentence supporting a claim is hard to find or does not exist. This creates a
trust gap for students, researchers, builders, and decision-makers.

## Solution

SYNAPSE rebuilds the research workflow around evidence integrity:

1. Plan the research question into focused jobs.
2. Search and fetch real sources.
3. Extract claims only with source quotes.
4. Verify claims into a fact ledger.
5. Synthesize an answer using fact IDs.
6. Audit the answer against user intent and unsupported claims.
7. Apply visible patch operations with edit reasons and locations.
8. Validate the final artifact before calling it real.

## Audience

- Students who need trustworthy research help.
- Builders comparing technical options.
- Founders and analysts making decisions from public sources.
- Educators who want AI assistance without unverifiable citations.
- Teams that need audit trails for AI-generated reports.

## What Makes It Different

Most agent demos show a final answer. SYNAPSE shows the chain that produced it:

- source URL
- source quote
- evidence item
- fact ID
- verification status
- cited report section
- patch diff
- validator result
- run quality score

## Technical Highlights

- Async multi-stage research orchestration.
- Provider-first search, fetch, LLM, and reranking interfaces.
- Pydantic contracts between agents.
- Quote-grounded evidence extraction.
- Fact ledger with unsupported and contradiction handling.
- UI-ready patch diff metadata.
- Live validator for non-synthetic proof artifacts.
- Demo mode for reliable judging.

## UOE Summer of Code Fit

SYNAPSE fits the AI/ML, education technology, productivity, and open innovation
themes. It addresses a real-world problem: making AI-generated research usable
without asking users to blindly trust model prose.

## Demo Promise

The demo should show a hard research question, then reveal the full evidence
chain behind the answer: fetched sources, quotes, fact ledger, unsupported
claims, patch operations, and validator pass.
