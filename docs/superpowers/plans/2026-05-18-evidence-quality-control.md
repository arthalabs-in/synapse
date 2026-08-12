# Evidence Quality Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve SYNAPSE's answer quality as a general solution by making planner intent, source fitness, evidence fitness, coverage, and synthesis constraints explicit and auditable.

**Architecture:** Add a lightweight evidence-quality layer between planning/search/extraction/synthesis. The planner defines what good evidence should cover, reranking prioritizes sources that match that intent, extraction labels what each quote actually supports, the engine builds a coverage matrix, and synthesis receives that matrix so it cannot over-rely on a narrow or irrelevant source.

**Tech Stack:** Python, Pydantic v2, pytest, existing provider-first pipeline, Streamlit UI consumers via existing `PipelineResult.run_quality` and provider metrics.

---

## File Map

- `backend/models.py`: add evidence criteria and evidence-fit fields to stable schemas.
- `backend/evidence_quality.py`: new pure scoring module for query intent, source fitness, evidence fitness, and coverage matrices.
- `agents/planner.py`: make planner output include evidence criteria and coverage requirements.
- `backend/reranker.py`: use source fitness when selecting search headers and fetched sources.
- `agents/evidence_extractor.py`: ask LLM and deterministic fallback to tag evidence target, dimension, and fit.
- `agents/synthesizer.py`: inject coverage matrix and evidence limitations into the synthesis prompt.
- `agents/coverage_auditor.py`: flag unsupported broad claims and missing coverage.
- `backend/research_engine.py`: compute and expose coverage/quality data in `run_quality`.
- `frontend/app.py`: display quality/coverage in human labels only, no snake_case IDs.
- `tests/test_evidence_quality.py`: new scoring and coverage tests.
- `tests/test_models.py`: schema defaults for new fields.
- `tests/test_reranker.py`: ranking behavior with source fitness.
- `tests/test_searcher_extractor.py`: extraction parsing/fallback behavior.
- `tests/test_synthesizer.py`: prompt includes coverage and limitations.
- `tests/test_research_engine.py`: pipeline result contains quality matrix.

---

## Task 1: Add Evidence Quality Contracts

- [ ] Add small Pydantic models to `backend/models.py`.

```python
class CoverageRequirement(SynapseModel):
    requirement_id: str
    label: str
    description: str
    required_targets: list[str] = Field(default_factory=list)
    required_dimensions: list[str] = Field(default_factory=list)


class EvidenceCriteria(SynapseModel):
    comparison_targets: list[str] = Field(default_factory=list)
    decision_dimensions: list[str] = Field(default_factory=list)
    preferred_source_types: list[str] = Field(default_factory=list)
    avoid_source_patterns: list[str] = Field(default_factory=list)
    source_fitness_terms: list[str] = Field(default_factory=list)
    narrow_source_warnings: list[str] = Field(default_factory=list)
    coverage_requirements: list[CoverageRequirement] = Field(default_factory=list)
```

- [ ] Add `evidence_criteria: EvidenceCriteria = Field(default_factory=EvidenceCriteria)` to `PlannerPrecontext`.
- [ ] Add these optional fit fields to `EvidenceItem`:

```python
target: str = ""
dimension: str = ""
evidence_fit_score: float = Field(default=0.0, ge=0.0, le=1.0)
evidence_fit_notes: list[str] = Field(default_factory=list)
```

- [ ] Add tests in `tests/test_models.py` verifying old minimal payloads still validate and new fields default safely.

Run:

```powershell
python -m pytest tests/test_models.py
```

---

## Task 2: Build the Evidence Quality Module

- [ ] Create `backend/evidence_quality.py`.
- [ ] Implement pure functions:

```python
def normalize_label(value: str) -> str: ...

def infer_query_targets(query: str) -> list[str]: ...

def infer_query_dimensions(query: str) -> list[str]: ...

def build_evidence_criteria(original_query: str, planner_output: PlannerPrecontext) -> EvidenceCriteria: ...

def score_source_fitness(
    original_query: str,
    planner_output: PlannerPrecontext,
    source: FetchedSource,
) -> dict[str, Any]: ...

def score_evidence_fitness(
    planner_output: PlannerPrecontext,
    evidence: EvidenceItem,
) -> dict[str, Any]: ...

def build_coverage_matrix(
    planner_output: PlannerPrecontext,
    evidence_items: list[EvidenceItem],
    fact_ledger: FactLedger | None = None,
) -> dict[str, Any]: ...
```

- [ ] Keep the heuristics simple:
  - reward direct query terms in title/text/domain,
  - reward evidence covering named targets and decision dimensions,
  - penalize narrow single-tool/vendor evidence when the query asks for a general recommendation,
  - penalize unverifiable snippets and generic blog summaries,
  - record plain-English notes for every penalty/reward.

- [ ] Add `tests/test_evidence_quality.py`:
  - a broad nonprofit/RAG/chatbot query should infer targets and dimensions,
  - an autonomous-vehicle source should score low for nonprofit citation workflow,
  - a source directly about nonprofit research/citation/retrieval should score higher,
  - coverage matrix should show missing dimensions.

Run:

```powershell
python -m pytest tests/test_evidence_quality.py
```

---

## Task 3: Make Planning Produce Evidence Criteria

- [ ] Update `agents/planner.py` prompt so it emits:
  - comparison targets,
  - decision dimensions,
  - preferred source types,
  - avoid patterns,
  - coverage requirements.

- [ ] Update planner fallback `_coverage_from_query()` so broad queries get concrete requirements, not generic labels.

Example requirement for the bad nonprofit answer:

```python
CoverageRequirement(
    requirement_id="cost_and_capacity",
    label="Cost and capacity",
    description="Compare setup cost, staff effort, and maintenance burden for each option.",
    required_targets=["general chatbot", "retrieval augmented chatbot", "source audited workflow"],
    required_dimensions=["cost", "implementation", "maintainability"],
)
```

- [ ] Ensure planner output never fails if LLM omits criteria: call `build_evidence_criteria()` as a repair step.

Run:

```powershell
python -m pytest tests/test_planner.py tests/test_models.py
```

---

## Task 4: Rank Sources by Fitness, Not Just Lexical Similarity

- [ ] Update `backend/reranker.py` to call `score_source_fitness()` inside `rank_fetched_sources()`.
- [ ] Store the result in `FetchedSource.metadata["source_fitness"]`.
- [ ] Blend score conservatively:

```python
combined = (0.45 * lexical_score) + (0.35 * source_quality) + (0.20 * source_fitness_score)
```

- [ ] Preserve existing deterministic behavior when no criteria exist.
- [ ] Ensure source selection keeps diversity across research jobs and targets.

- [ ] Add tests:
  - a directly relevant low-domain source should beat an irrelevant high-domain source,
  - a narrow source should not dominate a broad comparison,
  - at least three distinct fetched sources survive if available.

Run:

```powershell
python -m pytest tests/test_reranker.py
```

---

## Task 5: Tag Evidence With What It Actually Proves

- [ ] Update `agents/evidence_extractor.py` LLM schema/prompt to return:
  - `target`,
  - `dimension`,
  - `evidence_fit_score`,
  - `evidence_fit_notes`.

- [ ] The extractor must reject or downscore evidence where:
  - the quote is about a different domain than the query,
  - the quote supports only an analogy but synthesis would need a direct claim,
  - the quote is a tool limitation being generalized to all tools.

- [ ] Update deterministic fallback:
  - infer target/dimension from query/source/evidence text,
  - add a low score when the quote is only tangential,
  - keep quotes real and URL-linked.

- [ ] Add tests:
  - LLM extraction payload with target/dimension parses correctly,
  - old extraction payload still works with default fields,
  - fallback fills fit fields,
  - unrelated source evidence is low fit rather than promoted.

Run:

```powershell
python -m pytest tests/test_searcher_extractor.py tests/test_evidence_quality.py
```

---

## Task 6: Build and Expose a Coverage Matrix

- [ ] In `backend/research_engine.py`, after fact checking, call `build_coverage_matrix()`.
- [ ] Store it under:

```python
result.run_quality["coverage_matrix"] = coverage_matrix
result.run_quality["evidence_quality_summary"] = {
    "average_evidence_fit": ...,
    "missing_requirements": ...,
    "weak_requirements": ...,
    "strong_requirements": ...,
}
```

- [ ] Also expose a compact version in provider metrics for debug traces.
- [ ] Add tests ensuring a run with weak evidence is marked weak but still honest.

Run:

```powershell
python -m pytest tests/test_research_engine.py
```

---

## Task 7: Make Synthesis Coverage-Aware

- [ ] Update `agents/synthesizer.py` so the LLM receives:
  - original query,
  - top facts,
  - evidence limitations,
  - coverage matrix,
  - missing/weak requirements.

- [ ] Change the synthesis prompt policy:

```text
Write a decision memo, not a fact dump.
Use only verified or partial facts.
Do not generalize a narrow source into a broad claim.
If coverage is weak, say what is weak and how it affects the recommendation.
Every major recommendation must cite fact IDs that cover the relevant target and dimension.
Prefer a neutral comparison unless the evidence clearly supports a winner.
```

- [ ] Keep the output parseable by existing validators.
- [ ] Add tests with fake provider capturing prompt text:
  - coverage matrix is present,
  - evidence limitations are present,
  - sections still include fact IDs,
  - no section gets all fact IDs by default.

Run:

```powershell
python -m pytest tests/test_synthesizer.py
```

---

## Task 8: Audit Overreach Before Final Output

- [ ] Update `agents/coverage_auditor.py` to detect:
  - broad claims supported only by narrow evidence,
  - recommendations with missing coverage,
  - target comparisons where one target has no evidence,
  - citations that do not match the sentence they support.

- [ ] Add issue objects that include plain-English reason and suggested patch direction.
- [ ] Ensure patch/diff agent receives these reasons.
- [ ] Add tests where the bad nonprofit-style answer is flagged for:
  - irrelevant evidence domain,
  - overgeneralized ChatGPT citation claim,
  - GraphRAG-specific limitation generalized to RAG broadly.

Run:

```powershell
python -m pytest tests/test_coverage_auditor.py tests/test_diff_agent.py
```

---

## Task 9: Show Quality Without Exposing Internal IDs

- [ ] Update `frontend/app.py` to show:
  - coverage by topic,
  - evidence strength,
  - missing or weak areas,
  - source fit notes in human labels.

- [ ] Hide internal labels like:
  - `research_job_a`,
  - `source_fitness_score`,
  - `fact_a7`,
  - raw snake_case metadata keys.

- [ ] Use existing UI style: compact, dark, audit-oriented, no marketing hero.
- [ ] Add no new heavy frontend dependency.

Manual check:

```powershell
streamlit run frontend/app.py --server.port 8503
```

---

## Task 10: End-to-End Verification

- [ ] Run deterministic test suite.

```powershell
python -m pytest
```

- [ ] Run one cached/demo UI run and inspect quality display.
- [ ] Run one live research query with OpenCode Go `deepseek-v4-flash`.
- [ ] Inspect artifact:
  - source list is relevant,
  - evidence quotes match claims,
  - weak coverage is admitted,
  - final answer reads like a decision memo,
  - validator passes without silent fallback.

Suggested live test query:

```text
For a small nonprofit with limited technical staff, compare a general-purpose chatbot, a retrieval-augmented chatbot, and a source-audited research workflow for drafting grant proposals and policy briefs. Evaluate reliability, citation quality, implementation cost, staff usability, privacy risk, and long-term maintainability. Recommend the safest architecture and clearly state evidence gaps.
```

---

## Quality Gates

- [ ] No snippets treated as verified facts.
- [ ] No fabricated URLs.
- [ ] No deterministic fallback presented as LLM synthesis.
- [ ] Every final recommendation cites relevant fact IDs.
- [ ] Coverage gaps are visible to both the model and the user.
- [ ] UI displays human-readable labels only.
- [ ] `python -m pytest` passes.

---

## Self-Review

This plan keeps the solution general by adding reusable quality contracts instead of prompt-tuning one bad example. It avoids large dependencies and puts most logic in pure functions that can be tested deterministically. The riskiest schema changes are limited to additive fields with defaults, so existing artifacts and tests should remain compatible.
