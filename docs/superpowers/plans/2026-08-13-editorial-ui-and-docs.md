# Editorial UI and Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Editorial Light presentation, enlarge the blue signal slash in the SYNAPSE wordmark, and rewrite project documentation in a direct engineering voice without changing research behavior.

**Architecture:** Keep `frontend/app.py` responsible for Streamlit composition and `frontend/theme.py` responsible for visual markup and CSS. Add static theme tests that verify the approved design tokens and wordmark structure. Edit Markdown in place, preserving commands, contracts, limitations, and Horizons rules while removing duplicated promotional copy and authorship meta-commentary.

**Tech Stack:** Python 3.10+, Streamlit, HTML/CSS rendered through Streamlit, pytest, Markdown.

---

## File Map

- `frontend/theme.py`: replace the dark cockpit theme with the editorial token system; update helper markup and enlarged slash wordmark.
- `frontend/app.py`: simplify page composition into report-first main content and a quieter evidence/validation context column.
- `tests/test_frontend_theme.py`: static regression checks for colors, typography, wordmark, motion, and removed dark-theme decoration.
- `README.md`, `ARCHITECTURE.md`, `VERIFICATION_FRAMEWORK.md`: concise public technical documentation.
- `docs/ARCHITECTURE_OVERVIEW.md`, `docs/PROJECT_CHARTER.md`, `docs/GEMINI_CHARTER.md`, `docs/CAMOFOX_SETUP.md`: retain non-duplicated implementation and provider notes.
- `submission/*.md`, `submission/horizons/*.md`: factual deployment and submission checklists; no paste-ready application copy or writing-authorship meta text.

### Task 1: Theme Regression Contract

**Files:**
- Create: `tests/test_frontend_theme.py`
- Test: `tests/test_frontend_theme.py`

- [ ] **Step 1: Write failing static theme tests**

```python
from frontend import theme


def test_editorial_light_tokens_are_present():
    assert "--paper: #f3f0e8" in theme._CSS
    assert "--surface: #fbfaf6" in theme._CSS
    assert "--accent: #3157d5" in theme._CSS
    assert "Newsreader" in theme._CSS


def test_dark_dashboard_decoration_is_removed():
    assert "radial-gradient" not in theme._CSS
    assert "background-size: 42px 42px" not in theme._CSS


def test_wordmark_uses_enlarged_signal_slash():
    assert 'class="syn-logo-slash"' in theme.wordmark()
    assert ".syn-logo-slash" in theme._CSS
    assert "height: 3px" in theme._CSS


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion: reduce" in theme._CSS
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `python -m pytest tests/test_frontend_theme.py -q`

Expected: failures for missing editorial tokens and `wordmark()`.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/test_frontend_theme.py
git commit -m "Test editorial interface contract"
```

### Task 2: Editorial Theme and Wordmark

**Files:**
- Modify: `frontend/theme.py:21-1086`
- Modify: `frontend/theme.py:1290-1680`
- Test: `tests/test_frontend_theme.py`

- [ ] **Step 1: Replace the visual tokens and global Streamlit overrides**

Use these root tokens and remove the radial gradients, grid overlay, translucent dark panels, and neon status colors:

```css
:root {
  --paper: #f3f0e8;
  --surface: #fbfaf6;
  --ink: #171716;
  --soft: #68675f;
  --muted: #85837b;
  --line: #d6d1c5;
  --accent: #3157d5;
  --accent-soft: #e3e9ff;
  --ok: #25724b;
  --warn: #a15f15;
  --bad: #a33a32;
  --serif: "Newsreader", Georgia, serif;
  --sans: "DM Sans", system-ui, sans-serif;
  --mono: "JetBrains Mono", Consolas, monospace;
}
```

- [ ] **Step 2: Restyle existing helper classes**

Keep existing class names so call sites remain stable. Convert panels to plain sections with thin dividers; convert report headings and summaries to serif; keep metadata, IDs, and controls sans/mono; use the blue accent only for actions and references.

- [ ] **Step 3: Add restrained interaction and accessibility rules**

```css
@keyframes syn-enter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.block-container { animation: syn-enter 320ms ease-out both; }
.stButton > button:hover { transform: translateY(-1px); }
.syn-quote-card:hover, .syn-source-row:hover { background: #f7f4ed; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 4: Add the reusable enlarged signal-slash wordmark**

```python
def wordmark() -> str:
    return '<span class="syn-wordmark">SYN<span class="syn-logo-slash"></span>APSE</span>'
```

Render the slash at `width: 18px; height: 3px; transform: rotate(-56deg);` in the sidebar/header scale, with responsive reduction only below 640 px.

- [ ] **Step 5: Run the focused tests**

Run: `python -m pytest tests/test_frontend_theme.py -q`

Expected: `4 passed`.

- [ ] **Step 6: Commit the theme**

```bash
git add frontend/theme.py tests/test_frontend_theme.py
git commit -m "Apply editorial Streamlit theme"
```

### Task 3: Report-First Streamlit Composition

**Files:**
- Modify: `frontend/app.py:102-176`
- Modify: `frontend/app.py:474-750`
- Test: `tests/test_frontend_theme.py`

- [ ] **Step 1: Replace the three-column result grid**

Use a narrow workflow rail followed by a wide content area. Within the content area, render the grounded report beside evidence and integrity context. Preserve every renderer and place lower-priority sources, telemetry, patch detail, and export below the primary workspace.

```python
workflow, workspace = st.columns([0.20, 0.80], gap="large")
with workflow:
    render_workflow_rail(result)
    render_jobs(result)
with workspace:
    answer, context = st.columns([0.64, 0.36], gap="large")
    with answer:
        render_answer_workbench(result, report)
    with context:
        render_evidence_strip(result, limit=3)
        render_validation_inspector(result, report, ledger, patch)
    render_source_strip(result)
    render_provider_metrics(result)
    render_export(result)
```

- [ ] **Step 2: Make evidence rendering accept a display limit**

Change the signature to `render_evidence_strip(result: dict[str, Any], limit: int = 6) -> None`, use `items[:limit]`, and keep the expander for remaining items.

- [ ] **Step 3: Simplify opening copy and sidebar status**

Use the approved line “Trace every claim to its source.” and factual support copy. Remove repeated slogans from the sidebar while retaining provider/runtime state.

- [ ] **Step 4: Run frontend and full deterministic tests**

Run: `python -m pytest tests/test_frontend_theme.py tests/test_models.py tests/test_research_engine.py -q`

Expected: all selected tests pass.

- [ ] **Step 5: Commit the composition change**

```bash
git add frontend/app.py
git commit -m "Reorder research workbench content"
```

### Task 4: Technical Documentation Rewrite

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `VERIFICATION_FRAMEWORK.md`
- Modify: `docs/ARCHITECTURE_OVERVIEW.md`
- Modify: `docs/PROJECT_CHARTER.md`
- Modify: `docs/GEMINI_CHARTER.md`
- Modify: `docs/CAMOFOX_SETUP.md`

- [ ] **Step 1: Rewrite the README as the single public entry point**

Keep: one-paragraph description, pipeline diagram, demo/live setup, test and validator commands, directory map, and explicit limitations. Remove audience lists, taglines, submission framing, and repeated trust claims.

- [ ] **Step 2: Deduplicate architecture documents**

`ARCHITECTURE.md` owns stage responsibilities and contracts. `docs/ARCHITECTURE_OVERVIEW.md` becomes a compact diagram and link to the detailed file. Provider charters retain provider-specific behavior only.

- [ ] **Step 3: Rewrite verification language precisely**

State that validators check artifact consistency, URLs, quotes, fact IDs, patch references, and recorded degradation. Explicitly state that these checks do not independently prove factual truth.

- [ ] **Step 4: Convert the project charter into scope and non-goals**

Replace pitch/audience/originality sections with current scope, non-goals, operating assumptions, and known limitations.

- [ ] **Step 5: Scan for promotional and meta-writing phrases**

Run:

```powershell
rg -n -i "AI-assisted|AI written|AI-generated|best one-line pitch|what makes it different|why this matters|submission framing|proof points|tagline" -g "*.md"
```

Expected: no matches outside historical design/plan documents.

- [ ] **Step 6: Commit technical docs**

```bash
git add README.md ARCHITECTURE.md VERIFICATION_FRAMEWORK.md docs
git commit -m "Tighten technical documentation"
```

### Task 5: Submission Notes Cleanup

**Files:**
- Modify: `submission/README.md`
- Modify: `submission/DEPLOY.md`
- Remove: `submission/short_description.md`
- Remove: `submission/long_description.md`
- Modify: `submission/horizons/README.md`
- Modify: `submission/horizons/ship_checklist.md`

- [ ] **Step 1: Remove paste-ready application copy**

Delete the short and long description drafts. They are not technical project documentation and Horizons requires the project description to be written by the submitter.

- [ ] **Step 2: Make the submission README an asset and readiness index**

Keep only links to deployment steps, Horizons rules/checklist, repository URL, demo URL placeholder, and a short list of proof artifacts reviewers can inspect.

- [ ] **Step 3: Keep deployment steps operational**

Retain exact environment values, Streamlit entry point, private-window check, test command, and live validator command. Remove judge-script and pitch language.

- [ ] **Step 4: Correct stale repository statements**

State that the repository remote is `https://github.com/arthalabs-in/synapse` and remove claims that the checkout has no Git history.

- [ ] **Step 5: Scan all submission Markdown**

Run: `rg -n -i "pitch|audience|originality|AI-assisted|paste|suggested description" submission -g "*.md"`

Expected: no application-copy or authorship-meta matches.

- [ ] **Step 6: Commit submission notes**

```bash
git add submission
git commit -m "Reduce submission notes to factual checklists"
```

### Task 6: Visual and Full Verification

**Files:**
- Modify only if verification exposes defects: `frontend/theme.py`, `frontend/app.py`

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Start the demo UI**

Run: `$env:DEMO_MODE='true'; $env:GOLDEN_RESULT_PATH='tests/fixtures/demo_golden.json'; streamlit run frontend/app.py --server.headless true`

Expected: Streamlit reports a local URL and loads without an exception.

- [ ] **Step 3: Capture desktop and narrow viewport screenshots**

Verify the initial query view and `?demo=1` populated view at approximately 1440 px and 390 px widths. Check hierarchy, contrast, responsive stacking, wordmark slash, evidence readability, controls, and download access.

- [ ] **Step 4: Run final repository checks**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; only intended changes remain.

- [ ] **Step 5: Commit any verification fixes**

```bash
git add frontend tests README.md ARCHITECTURE.md VERIFICATION_FRAMEWORK.md docs submission
git commit -m "Polish Horizons presentation"
```

## Human Summary

The implementation keeps SYNAPSE's research pipeline intact. It changes the Streamlit presentation to the approved warm editorial style, gives the wordmark a larger blue slash, and rearranges results so the report and its evidence are easier to read together. Existing Markdown remains where it contains useful setup, architecture, provider, verification, deployment, or Horizons information; repetitive application copy and writing-process commentary are removed. The work finishes with deterministic tests plus desktop and mobile visual checks.
