# SYNAPSE Submission Assets

All submission-specific material for hackathon or program submissions lives here.
Horizons-specific material (the target program for this repo) lives in
`horizons/`; everything else is kept competition-agnostic.

## Horizons Pack

| File | Purpose |
| ---- | ------- |
| `horizons/README.md` | How Horizons qualification works + SYNAPSE-specific rules |
| `horizons/ship_checklist.md` | Pre-ship readiness checklist for the Ship Wizard |

## Asset Index

| File | Purpose |
| ---- | ------- |
| `short_description.md` | Short submission pitch |
| `long_description.md` | Detailed problem / solution / implementation description |
| `submission_answers.md` | Paste-ready submission answers |
| `demo_runbook.md` | Exact recording flow, showcase query, and screenshot list |
| `winning_checklist.md` | Judging checklist and final launch gate |
| `slides/slides.md` | Marp slide deck source |
| `slides/README.md` | Export instructions |
| `video_script.md` | Walkthrough video script |
| `cover_image.svg` | Cover art placeholder |
| `DEPLOY.md` | Deployment checklist |
| `build_in_public.md` | General build-in-public posts |

## Recommended Submission Framing

**Project category:** Artificial Intelligence & Machine Learning, Education
Technology, Startup & Productivity Solutions, or Open Innovation.

**Core pitch:** SYNAPSE makes AI research trustworthy by grounding every final
claim in source quotes, fact IDs, validator checks, and visible patch decisions.

## Proof Points To Include

- Full unit suite passes.
- Live golden validation passes.
- Demo mode works without live APIs.
- Every accepted evidence item includes a source quote.
- Unsupported claims are tracked and blocked from final reports.
- Patch diff metadata explains what changed, where, and why.

## Suggested Demo Flow

1. Run or load a hard research query.
2. Show source fetches and quote-grounded evidence.
3. Show fact ledger statuses.
4. Show unsupported claim handling.
5. Show final report and patch diff.
6. Run the validator.

## Best Current Showcase Query

```text
A small nonprofit education organization wants to use AI to produce trustworthy research reports for grant writing, policy briefs, and student support programs. Compare three approaches: using a general-purpose chatbot, building a retrieval-augmented chatbot over selected documents, and building a source-audited research workflow that searches the web, extracts direct quotes, verifies claims, and blocks unsupported statements. Evaluate reliability, citation quality, implementation complexity, cost, usability for non-technical staff, data/privacy risks, and long-term maintainability. Recommend the best approach for a team with limited budget, limited engineering capacity, and high need for trust.
```

## Manual Items Still Needed

- Add final GitHub URL.
- Add final demo URL or reliable local demo note.
- Record and upload the walkthrough video.
- Capture final screenshots from the best run.
- Paste the strongest answer from `submission_answers.md` into your program's submission form.
