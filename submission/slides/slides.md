---
marp: true
theme: default
paginate: true
size: 16:9
title: SYNAPSE - Answers You Can Audit
---

# SYNAPSE
## Answers you can audit

An evidence-first AI research agent for trustworthy knowledge work.

---

## The Problem

- AI research assistants sound confident even when evidence is weak.
- Links often do not support the exact claim being made.
- Users need to know: "Where did this statement come from?"

---

## The Idea

SYNAPSE turns every answer into an audit trail:

**source -> quote -> evidence -> fact ID -> report section -> patch diff -> validator**

---

## Pipeline

```text
query
  -> Planner
  -> Searcher + SourceFetcher
  -> EvidenceExtractor
  -> FactChecker
  -> Synthesizer(report_v1)
  -> CoverageAuditor
  -> PatchApplicator(report_v2)
  -> Validator
```

---

## What Makes It Different

- Search snippets are not treated as verified facts.
- Every evidence item needs a source quote.
- Facts are classified as verified, partial, unsupported, or contradicted.
- The final answer cites fact IDs.
- Patch operations explain what changed, where, and why.

---

## Technical Complexity

- Async multi-agent orchestration.
- Provider-first search, fetch, LLM, and reranking interfaces.
- Pydantic schemas across every stage.
- Semantic source reranking.
- Source quality scoring and cleaning.
- Live validator for non-synthetic proof artifacts.

---

## Product Experience

Judges can inspect:

- fetched sources
- source quotes
- fact ledger
- unsupported claims
- report citations
- colored patch diff
- run quality
- validator result

---

## Impact

SYNAPSE helps students, researchers, builders, and teams use AI research without
blind trust.

It is not just an answer generator. It is an evidence integrity layer.

---

## Verification

- Unit tests pass locally.
- Live golden artifacts validate.
- Validator rejects fake URLs, missing quotes, unsupported leaks, bad patch
  operations, and silent model fallback.

---

## Ask

Try SYNAPSE on a hard research question.

Then inspect the proof behind the answer.

GitHub: `github.com/<you>/synapse`
