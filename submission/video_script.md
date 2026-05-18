# SYNAPSE Demo Video Script

Target length: 2:30 to 3:30. Record at 1920x1080.

## 0:00-0:20 - Hook

**Visual:** open the SYNAPSE UI on the empty workbench.

**Voiceover:**
> Most AI tools ask you to trust fluent text. SYNAPSE gives you the evidence
> chain behind the answer. It is built for one promise: answers you can audit.

## 0:20-0:55 - Ask A Hard Question

**Visual:** paste the nonprofit education showcase query.

**Voiceover:**
> I start with a realistic nonprofit education question. SYNAPSE does not jump
> straight to a summary. It plans the research, searches public sources, fetches
> readable pages, and prepares evidence for verification.

## 0:55-1:15 - Live Pipeline

**Visual:** show Plan, Search, Fetch, Extract, Ledger, Draft, Audit, Patch
updating live.

**Voiceover:**
> The workflow is visible while it runs. Each stage has a job: plan, search,
> fetch, extract quotes, reconcile facts, draft, audit, and patch.

## 1:15-1:50 - Evidence Trail

**Visual:** show fetched sources and evidence cards.

**Voiceover:**
> Every evidence item has a real URL and an exact source quote. Search snippets
> are not enough. If a claim cannot be grounded in fetched text, it does not
> become a verified fact.

## 1:50-2:20 - Fact Ledger

**Visual:** show verified, partial, unsupported, and contradiction sections.

**Voiceover:**
> The fact checker creates a ledger. Some claims are verified. Some are partial.
> Some are unsupported and blocked from the final answer. This is the difference
> between a chatbot and an auditable research system.

## 2:20-2:50 - Patch Diff

**Visual:** show report v1, coverage audit, patch operations, and report v2.

**Voiceover:**
> The coverage auditor compares the answer to the original question and the
> evidence ledger. When it patches the report, each edit includes an ID, a
> location, a reason, the original text, and the replacement text. This is built
> so the UI can show exactly what changed and why.

## 2:50-3:10 - History

**Visual:** open the History tab.

**Voiceover:**
> Completed runs are saved with their prompt, answer summary, evidence count,
> source count, and review status, so users can compare previous research.

## 3:10-3:30 - Validator Proof

**Visual:** terminal command:

```bash
python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

**Voiceover:**
> Every run writes a JSON artifact. The validator rejects fake URLs, missing
> quotes, unsupported claims leaking into the final report, bad patch
> operations, and silent model fallback. If it passes, the result is auditable.

## 3:30-3:45 - Close

**Visual:** show final report and run quality metrics.

**Voiceover:**
> SYNAPSE is for students, nonprofits, researchers, builders, and teams who need
> trust, not just fluent text. It turns AI answers into evidence trails.

**End card:** SYNAPSE - Answers you can audit.
