# Artifact verification

Pipeline output is treated as untrusted structured data. Validation checks that
the artifact is internally consistent and that its evidence trail can be
inspected.

## Checks

### Sources

- URLs must use public HTTP or HTTPS locations.
- A live artifact must contain fetched sources and provider metrics.
- Failed fetches remain visible in the artifact.

### Evidence

- Each item includes a source URL, title, quote, extraction method, and quality
  metadata.
- The quote must be non-empty and anchored to fetched text when that text is
  available.
- Snippet fallbacks are labelled and limited.

### Fact ledger

- Facts are separated into verified, partial, unsupported, and contradicted
  groups.
- Supporting evidence IDs must resolve.
- Report sections and key findings may cite only known fact IDs.

### Patches

- Each operation identifies a target and reason.
- At least one referenced fact, contradiction, or result must resolve.
- Unsupported replacement text is rejected by the patch applicator.

### Degradation

- Empty visible model output is an error.
- Reasoning truncation and deterministic fallback are recorded.
- A successful model request followed by an unreported fallback fails live
  artifact validation.

## Commands

```bash
python -m pytest
```

```bash
python scripts/run_live_golden.py \
  --query "What are the strongest evidence-backed approaches for building a trustworthy research assistant?" \
  --out artifacts/live_golden_run.json \
  --trace artifacts/live_golden_trace.md \
  --timeout 900
```

```bash
python scripts/validate_live_golden.py artifacts/live_golden_run.json
python scripts/audit_live_artifact.py artifacts/live_golden_run.json \
  --out artifacts/live_golden_audit.md
```

## Interpretation

A validator pass means required references exist and the recorded pipeline
behavior satisfies the checks above. It does not establish factual truth. A
reviewer can still reject a quote as weak support, a source as poor quality, or
a conclusion as an overreach.
