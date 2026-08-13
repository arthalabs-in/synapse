# Submission readiness

This directory contains deployment notes, public assets, and Horizons-specific
checks. Technical documentation stays at the repository root and in `docs/`.

## Links

- Repository: `https://github.com/arthalabs-in/synapse`
- README: `https://github.com/arthalabs-in/synapse/blob/lean-horizons/README.md`
- Public demo: add after deployment

## Files

| Path | Use |
| --- | --- |
| `DEPLOY.md` | public Streamlit deployment steps |
| `horizons/README.md` | current Horizons rules relevant to this project |
| `horizons/ship_checklist.md` | checks to complete before shipping |
| `short_description.md` | facts to cover in the submitter's own short description |
| `long_description.md` | facts to cover in the submitter's own project explanation |
| `architecture-diagram.png` | architecture asset; verify its origin before use |
| `cover_image.svg` | cover asset; verify its origin before use |

## Reviewable evidence

- deterministic test suite
- public source-fetching and evidence contracts
- demo fixture for stable UI review
- live artifact runner and validator
- fact ledger and patch operations in exported `PipelineResult` JSON

Descriptions submitted to Horizons should be written by the submitter. The two
description files list facts and constraints only; they are not copy to paste.
