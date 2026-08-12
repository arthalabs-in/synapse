# Demo Runbook

This is the exact path for recording the demo. Keep it tight: the goal is
to make judges understand SYNAPSE in the first 15 seconds, then prove it works.

## One-Sentence Demo Promise

SYNAPSE turns a hard research question into an answer you can audit: sources,
quotes, facts, validation, and patch reasons are all visible.

## Showcase Query

```text
A small nonprofit education organization wants to use AI to produce trustworthy research reports for grant writing, policy briefs, and student support programs. Compare three approaches: using a general-purpose chatbot, building a retrieval-augmented chatbot over selected documents, and building a source-audited research workflow that searches the web, extracts direct quotes, verifies claims, and blocks unsupported statements. Evaluate reliability, citation quality, implementation complexity, cost, usability for non-technical staff, data/privacy risks, and long-term maintainability. Recommend the best approach for a team with limited budget, limited engineering capacity, and high need for trust.
```

## Pre-Recording Checklist

- `python -m pytest` passes.
- UI starts at `http://127.0.0.1:8503`.
- `.env` is configured locally but not committed.
- Query box is empty on first load.
- Start button disables during a run.
- Pipeline stages update live.
- No old answer appears while a new run is running.
- History tab records completed runs.
- Browser zoom is 90-100% and the window is 1920x1080 if possible.

## Video Structure

### 0:00-0:15 - Hook

Visual: SYNAPSE empty workbench.

Say:

> Most AI tools give you a confident answer. SYNAPSE gives you an answer you
> can audit.

### 0:15-0:35 - Submit the Question

Visual: paste the showcase query and click Start Research.

Say:

> I am asking a realistic nonprofit research question. Instead of jumping
> straight to prose, SYNAPSE breaks the question into research stages.

### 0:35-1:05 - Live Pipeline

Visual: show Plan, Search, Fetch, Extract, Ledger, Draft, Audit, Patch moving.

Say:

> The pipeline is visible while it runs. It plans the research, searches public
> sources, fetches text, extracts quoted evidence, reconciles facts, drafts the
> answer, audits it, and applies justified edits.

### 1:05-1:45 - Evidence and Sources

Visual: show evidence cards and source cards.

Say:

> Every accepted evidence item has a real URL and a direct source quote. Search
> snippets are not treated as verified facts.

### 1:45-2:20 - Fact Ledger and Validator

Visual: show fact ledger, run quality, provider telemetry, validator.

Say:

> SYNAPSE separates verified, partial, and blocked claims. The validator exists
> to keep unsupported claims from quietly entering the final report.

### 2:20-2:50 - Patch Diff

Visual: show patch diff.

Say:

> The patch diff explains what changed, where it changed, and why. This is made
> for human review, not just model output.

### 2:50-3:10 - History

Visual: open History tab.

Say:

> Completed research runs are saved with the prompt, answer, evidence count,
> source count, and review status.

### 3:10-3:30 - Close

Visual: final answer.

Say:

> SYNAPSE is for students, nonprofits, builders, and teams who need AI speed
> without losing the evidence trail. Answers you can audit.

## Terminal Proof Shot

Use this at the end of the video or as a screenshot:

```powershell
python -m pytest
```

If you have a live artifact:

```powershell
python scripts\validate_live_golden.py artifacts\live_golden_run.json
```

## Screenshots To Capture

- Empty workbench.
- Pipeline running with one active animated stage.
- Final grounded answer.
- Evidence cards.
- Source cards.
- Validator and run quality.
- Patch diff.
- History tab.
- Terminal showing tests passing.

