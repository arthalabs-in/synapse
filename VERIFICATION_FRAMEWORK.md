# SYNAPSE Verification Framework

SYNAPSE treats AI output as untrusted until it passes schema, evidence, and
validator checks.

## What We Verify

### 1. Source Reality

The live validator rejects reports when:

- no real URLs exist
- URLs are fake, local, or synthetic
- fewer than three fetched sources exist
- provider metrics are missing

### 2. Evidence Grounding

Evidence must include:

- source URL
- source title
- exact source quote
- fetched source ID where available
- extraction method
- source quality score
- limitations where applicable

Search snippets alone are not treated as verified facts.

### 3. Fact Ledger Integrity

The fact checker separates:

- `VERIFIED` facts
- `PARTIAL` facts
- unsupported claims
- contradictions
- dropped evidence

The synthesizer must cite fact IDs in report sections and key findings.

### 4. Patch Safety

Patch operations must include at least one valid reference:

- `fact_ids`
- `contradiction_ids`
- `result_ids`

Patch operations also carry UI-ready metadata:

- `edit_id`
- `target_path`
- `edit_label`
- `original_text`
- `replacement_text`
- `reason`

This lets a UI show exactly what changed, where it changed, and why the edit is
grounded.

### 5. Silent Fallback Detection

The validator checks for silent deterministic fallback after successful LLM
calls. If a model call returns zero visible content or the synthesizer falls
back without recording degradation, validation fails.

### 6. Run Quality

Each run includes a quality score and signals:

- fetched source count
- successful fetch rate
- evidence count
- LLM evidence count
- fallback evidence count
- snippet evidence count
- average source quality
- verified / partial / unsupported fact counts
- contradiction count
- report confidence
- coverage score
- degraded mode

## Commands

Run deterministic tests:

```bash
python -m pytest
```

Run a live trace:

```bash
python scripts/run_live_golden.py --query "What are the strongest evidence-backed approaches for building a trustworthy AI research assistant?" --out artifacts/live_golden_run.json --trace artifacts/live_golden_trace.md --timeout 900
```

Validate the live trace:

```bash
python scripts/validate_live_golden.py artifacts/live_golden_run.json
```

Build a causal audit markdown report:

```bash
python scripts/audit_live_artifact.py artifacts/live_golden_run.json --out artifacts/live_golden_audit.md
```

## Current Proof Points

- Unit suite passes locally.
- Existing live golden artifacts validate.
- UI-ready diff artifact validates.
- Validator catches fake URLs, missing quotes, unsupported leaks, bad patch
  operations, and silent LLM degradation.

## Trust Claim

SYNAPSE does not claim every model output is true. It claims every accepted
answer is auditable: the user can inspect the source quote, fact ID, report
section, patch operation, validator result, and quality signals that produced
the answer.
