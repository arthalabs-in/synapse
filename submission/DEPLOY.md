# SYNAPSE Deployment Notes

These notes are for producing a public prototype link for judging.

## Preferred Demo Strategy

Use demo mode for the public prototype:

```env
DEMO_MODE=true
GOLDEN_RESULT_PATH=tests/fixtures/demo_golden.json
```

Demo mode loads a validated artifact and avoids live API failures during judging.
Live mode can still be shown locally or in the video.

## Streamlit Community Cloud

1. Push a clean GitHub repository.
2. Ensure `.env` is not committed.
3. Add secrets in Streamlit settings:

```toml
DEMO_MODE = "true"
GOLDEN_RESULT_PATH = "tests/fixtures/demo_golden.json"
```

4. Set the app entrypoint:

```text
frontend/app.py
```

5. Deploy and test the public URL.

## Hugging Face Spaces

1. Create a Streamlit Space.
2. Upload the repository.
3. Add secrets in Space settings.
4. Confirm `requirements.txt` installs successfully.
5. Launch `frontend/app.py`.

## Local Live Run

For a real live artifact:

```bash
python scripts/run_live_golden.py --query "What are the strongest evidence-backed approaches for building a trustworthy AI research assistant?" --out artifacts/live_golden_run.json --trace artifacts/live_golden_trace.md --timeout 900
python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

## Public Repo Checklist

- [ ] `.env` removed.
- [ ] `.gitignore` present.
- [ ] API keys stored only in deployment secrets.
- [ ] Demo mode works without live APIs.
- [ ] `python -m pytest` passes.
- [ ] `scripts/validate_live_golden.py` passes on chosen artifact.
- [ ] README links to architecture and verification docs.
- [ ] Submission includes demo URL, GitHub URL, slides, and video.

## Judge Flow

The deployed site should make it easy to inspect:

- query
- planner output
- fetched sources
- evidence quotes
- fact ledger
- unsupported claims
- final answer
- patch diff
- run quality
- validator result
