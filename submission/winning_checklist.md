# Winning Checklist

The goal is not just to submit. The goal is to look more complete, more useful,
and more trustworthy than generic AI submissions.

## UOE Judging Criteria

### Innovation

- [x] Clear thesis: "answers you can audit."
- [x] Goes beyond chatbot output.
- [x] Evidence chain is part of the product.
- [x] Patch diff turns model correction into visible review metadata.
- [ ] In the video, explicitly say why this is different from normal chatbots.

### Implementation

- [x] Multi-stage backend pipeline.
- [x] Provider-first search/fetch/LLM architecture.
- [x] Pydantic contracts between agents.
- [x] Live progress events from backend to frontend.
- [x] Run history.
- [x] Validator and test suite.
- [ ] Final public demo URL or reliable local demo instructions.

### Usability

- [x] Empty query mode.
- [x] Start button blocks while running.
- [x] Pipeline stages show progress.
- [x] Source/evidence/fact/patch panels are visible.
- [x] History tab stores prior prompts and answers.
- [ ] Capture screenshots at a clean browser size.
- [ ] Make sure final showcase answer is readable and impressive.

### Impact

- [x] Strong audience: students, nonprofits, researchers, founders, analysts.
- [x] Real problem: AI answers are hard to verify.
- [x] Clear value: faster research with preserved audit trail.
- [ ] Submission text should mention nonprofit/education example.
- [ ] Video should show why unsupported-claim blocking matters.

### Presentation

- [x] Devpost-ready copy exists.
- [x] Demo runbook exists.
- [x] Video script exists.
- [x] Architecture docs exist.
- [ ] Record 2-3 minute video.
- [ ] Add screenshots to README or submission page.
- [ ] Add demo link.
- [ ] Add GitHub link.

## Final Engineering Gate

Run:

```powershell
python -m pytest
```

Expected at time of writing:

```text
168 passed
```

Check:

- [ ] `.env` is not committed.
- [ ] API keys are not in screenshots, video, docs, or artifacts.
- [ ] App opens at the submitted demo link or local instructions work.
- [ ] Demo mode works if live APIs fail.
- [ ] The showcase run has real URLs and direct quotes.

## Submission Links To Fill

- GitHub:
- Demo:
- Video:
- Slides or Documentation:
- Team:

## 30-Second Pitch

Most AI tools ask users to trust fluent text. SYNAPSE makes the evidence chain
visible. It searches public sources, fetches source text, extracts direct
quotes, reconciles claims into a fact ledger, blocks unsupported statements, and
shows patch reasons for every final edit. It is an AI research workbench for
students, nonprofits, researchers, and builders who need answers they can audit.

