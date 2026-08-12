# SYNAPSE at Horizons — Submission Guide

Horizons is Hack Club's 2026 flagship hackathon series (Nexus/SF, Polaris/
Toronto, Arcana/Singapore, Europa/Central Europe, Sol/South America,
Crux/Australia, Equinox/Africa). It is a **hours-based** program: you qualify
by shipping approved project time on the Horizons platform, not by entering a
one-shot contest.

Everything in this folder is Horizons-specific. The rest of the repo stays
competition-agnostic on purpose.

## Qualification model (the part that matters)

- You accumulate **approved** shipping hours. Qualifying: **30 hours** for
  Horizons Nexus (San Francisco), **35 hours** for every other Horizons event.
- Hours are tracked automatically by **Hackatime** (code) and **Lapse**
  (art/music). Art/music may be at most **1/3** of total logged time.
- **Only time logged after Feb 22, 2026 counts** — even for an existing
  project like SYNAPSE.
- Each ship needs **>= 3 hours** of tracked time on that project. A
  resubmission needs >= 3 additional hours beyond the last approved ship.
- Hours only **bank when a ship is approved** by a human reviewer. Raw
  tracked time is not approved time.

With 65+ hours already recorded, the volume is not the constraint — the
constraint is making sure those hours are (a) on Hackatime, (b) after the
Feb 22 cutoff, (c) attached to the project you create, and (d) approved.

## Ship flow (what happens on the platform)

1. Sign in at horizons.hackclub.com with **Hack Club Auth**, finish
   onboarding, **link Hackatime**.
2. **Create the project**: title, description, select the Hackatime
   project(s) to count. Project must be in a usable "demo" state.
3. **Ship Wizard** (5 steps):
   - Presubmit: requirements checklist (README, AI disclosure).
   - Project: URLs for **demo, code, README** + Hackatime selection. URLs are
     live-checked server-side — broken links block shipping.
   - Personal: mailing address + Hack Club ID verification gate.
   - Integrity: authorship + rule-compliance confirmation.
   - Finish: submit for review.
4. Review: `pending` -> `approved` / `rejected`. If rejected, fix per
   feedback and ship again with 3+ new hours.

## Rules that specifically affect SYNAPSE

| Rule | What to do |
| ---- | ---------- |
| All projects must be open source on GitHub or a similar forge | Push this repo to a **public** GitHub repo (this working copy has no `.git` — see below). |
| Demo URL must be reachable | Deploy the Streamlit app (Community Cloud / HF Spaces / Render). Demo mode works offline but the URL itself must respond. |
| No "AI slop" — projects must look polished and human-made | SYNAPSE is an AI *tool*, which is allowed; it must not look like a vibecoded wrapper. |
| Don't write project descriptions/updates with AI | Rewrite the description you paste into the platform in your own words, even though the repo copy here was AI-assisted. |
| No generative AI for graphics/audio | Confirm `submission/cover_image.svg` and any other media are not AI-generated. |
| No double-dipping with other Hack Club programs (except Sleepover) | SYNAPSE was previously submitted to UOE Summer of Code. If UOE is a Hack Club program, this blocks Horizons — verify with horizons@hackclub.com or #horizons-help before committing hours to it. |
| Teams allowed; hours logged separately; art/music <= 1/3 | Solo submission avoids the split. |
| No video required | Horizons reviewers check the project + live demo URL. The demo runbook and video script are optional extras, not requirements. |

## Pre-ship checklist

Run through `ship_checklist.md` before opening the Ship Wizard.

## Contacts

- horizons@hackclub.com
- `#horizons-help` on the Hack Club Slack
- Events list: horizons.hackclub.com/app/events (events run June-August 2026 —
  check your target event's deadline; SF Nexus was June 19-21).
