# Public demo deployment

Deploy the Streamlit app in demo mode so reviewers do not need provider keys.

## Settings

```env
DEMO_MODE=true
GOLDEN_RESULT_PATH=tests/fixtures/demo_golden.json
```

Entrypoint:

```text
frontend/app.py
```

## Streamlit Community Cloud

1. Connect the public repository.
2. Select `frontend/app.py` as the app file.
3. Add the two settings above as secrets.
4. Deploy.
5. Open the URL in a private browser window.
6. Load `?demo=1` and check the populated research view.

Do not add `.env` or provider keys to the repository.

## Before sharing the URL

```bash
python -m pytest
streamlit run frontend/app.py
```

For a current live artifact, run:

```bash
python scripts/run_live_golden.py \
  --query "What are the strongest evidence-backed approaches for building a trustworthy research assistant?" \
  --out artifacts/live_golden_run.json \
  --trace artifacts/live_golden_trace.md \
  --timeout 900

python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

Check that the public app loads, the demo fixture renders, downloads work, and
no secret or local path appears in the UI.
