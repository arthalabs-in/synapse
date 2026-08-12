# Horizons Ship Checklist — SYNAPSE

Run every item before opening the Ship Wizard. Anything unchecked is a
likely rejection or a wasted ship.

## GitHub (required: open source)

- [ ] Working copy pushed to a **public** GitHub repo (this folder has no
      `.git` — `git init`, commit, push to a new repo such as
      `arthalabs-in/synapse-horizons`).
- [ ] `.env`, `.streamlit/secrets.toml`, `artifacts/`, and `huashu-design/`
      are not committed (`.gitignore` already covers them — verify after
      init).
- [ ] README at repo root renders and describes the project (human-written —
      AI policy).
- [ ] Repo README URL resolves to the actual README file (the wizard
      auto-fills `…/blob/main/README.md` from the repo URL — check it).

## Demo URL (required: live)

- [ ] Streamlit app deployed publicly (Community Cloud / HF Spaces / Render)
      per `submission/DEPLOY.md`.
- [ ] URL returns a working page when opened in a private browser tab. The
      wizard pings the URL server-side; a 404 or auth wall fails the check.
- [ ] `DEMO_MODE=true` with `GOLDEN_RESULT_PATH=tests/fixtures/demo_golden.json`
      so the public demo is stable without API keys (see
      `.streamlit/secrets.toml.example`).
- [ ] Live mode still works locally with `GEMINI_API_KEY` for your own
      recording/verification.

## Hours (required: >= 3 per ship, all after Feb 22, 2026)

- [ ] waka.hackclub.com shows the 65+ hours under the Hackatime project
      name(s) you will select.
- [ ] Logged dates are all **after 2026-02-22** (pre-cutoff hours do not
      count, even on an existing project).
- [ ] Art/music (Lapse) is at most 1/3 of total logged time, if used.
- [ ] At least 3 of the hours are attached to the project you are shipping
      (the wizard shows live eligibility).
- [ ] You know the exact Hackatime project name(s) to select in the wizard —
      note them down before creating the Horizons project.

## Platform account

- [ ] horizons.hackclub.com onboarding complete.
- [ ] Hackatime account linked to Horizons.
- [ ] Mailing address present on your Hack Club profile (Ship Wizard
      "Personal" step gates on it).
- [ ] Hack Club ID verification done (HCA), or re-auth sync ready
      (Ship Wizard has a RE-AUTH button for this).
- [ ] Double-dip check: if SYNAPSE was submitted to another Hack Club
      program (e.g. UOE Summer of Code), confirmed with horizons@hackclub.com
      that Horizons is allowed.

## Project description (AI policy)

- [ ] Title + description drafted **by you, in your own words** — no AI
      writing in the platform text.
- [ ] Description makes the evidence-first angle concrete: quote-grounded
      claims, fact ledger, patch diffs, validator — not "AI research
      assistant" boilerplate.
- [ ] Graphics/audio in the submission (cover image, any media) are not
      generative-AI output.

## After shipping

- [ ] Status changes from `pending`; if rejected, read the reviewer feedback,
      fix, log 3+ more hours, reship.
- [ ] Approved hours bank toward the 30 (Nexus) / 35 (other events) target.
