# Repository Guidelines

## Project Structure & Module Organization

SYNAPSE is a Python multi-agent research pipeline skeleton. Agent role stubs live in `agents/`: planning, searching, evidence extraction, fact checking, synthesis, and gap detection. Stable data contracts and orchestration support live in `backend/`; keep shared schemas in `backend/models.py` and reusable validation in `backend/validators.py`. The Streamlit prototype is in `frontend/app.py`, tests are in `tests/`, and planning docs live in `docs/`. Configuration starts from `config.py` and `.env.example`.

## Current Architecture Rules

This repository is provider-first. Keep agent responsibilities separate: search returns `SearchHeader`, fetching returns `FetchedSource`, extraction returns quote-grounded `EvidenceItem`, fact checking returns `FactLedger`, and synthesis/auditing/patching must not invent new facts. Demo mode must remain available and live failures must be reported honestly.

## Build, Test, and Development Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run all tests:

```bash
pytest
```

Run only schema tests:

```bash
pytest tests/test_models.py
```

Run the UI prototype only when working on frontend behavior:

```bash
streamlit run frontend/app.py
```

## Coding Style & Naming Conventions

Use Python 3.10+ style with 4-space indentation and clear `snake_case` names for modules, functions, variables, and tests. Use `PascalCase` for Pydantic models. Prefer Pydantic v2 APIs such as `field_validator`, `model_validator`, `ConfigDict`, and `model_dump()`. Avoid mutable defaults; use `Field(default_factory=...)`.

## Testing Guidelines

Tests use `pytest`. Place tests under `tests/` and name files `test_<area>.py`. Add schema tests when changing `backend/models.py`, and validation tests when changing `backend/validators.py`. Tests should be deterministic and should not require live LLM endpoints, external search APIs, or Streamlit startup.

## Commit & Pull Request Guidelines

No Git history is available in this checkout, so use concise imperative commit messages such as `Add pipeline result schema` or `Validate report citations`. Pull requests should include a summary, test results, linked issue or doc when relevant, and screenshots only for UI changes.

## Security & Configuration Tips

Do not commit `.env`, API keys, endpoint URLs, or generated reports containing sensitive data. Treat search results and model output as untrusted input. Preserve URL, quote, citation, and fact-id validation when changing pipeline behavior.

## Live Provider Rules

Do not treat snippets as verified facts. Snippets may only be low-confidence fallback evidence with explicit limitations. Use provider interfaces under `backend/providers/`; agents should not import OpenCode Go, vLLM, DuckDuckGo, arXiv, or Camofox implementations directly. Camofox is optional and only for public JS-heavy pages when HTTP fetch is insufficient.
