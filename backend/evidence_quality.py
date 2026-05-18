"""Evidence/source fitness helpers for coverage-aware research quality."""

from __future__ import annotations

import re
from typing import Any

from backend.models import (
    CoverageRequirement,
    EvidenceCriteria,
    EvidenceItem,
    FactLedger,
    FetchedSource,
    PlannerPrecontext,
)


_DIMENSION_ALIASES: dict[str, set[str]] = {
    "reliability": {"reliability", "accuracy", "hallucination", "trust", "failure", "quality"},
    "citation quality": {"citation", "citations", "source", "sources", "reference", "grounding"},
    "implementation cost": {"cost", "budget", "pricing", "expense", "compute", "storage", "indexing"},
    "staff usability": {"usability", "staff", "workflow", "training", "capacity", "nontechnical"},
    "privacy risk": {"privacy", "security", "sensitive", "data", "breach", "risk"},
    "maintainability": {"maintainability", "maintenance", "support", "operations", "monitoring"},
    "implementation complexity": {"implementation", "complexity", "engineering", "integration", "deployment"},
    "evaluation": {"evaluation", "benchmark", "measure", "validate", "testing"},
}

_TARGET_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("general-purpose chatbot", ("general-purpose chatbot", "general purpose chatbot", "chatgpt", "claude", "all-purpose ai")),
    ("retrieval-augmented chatbot", ("retrieval-augmented", "retrieval augmented", "rag", "graphrag")),
    ("source-audited research workflow", ("source-audited", "source audited", "audited research", "citation workflow", "evidence-grounded")),
    ("custom async python", ("custom async python", "custom python")),
    ("langgraph", ("langgraph",)),
    ("gemini adk", ("gemini adk", "adk-native", "adk native")),
]


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", value or "")).strip().lower()


def infer_query_targets(query: str) -> list[str]:
    lowered = normalize_label(query)
    targets = []
    for label, patterns in _TARGET_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            targets.append(label)
    if " compare " in f" {lowered} ":
        fragments = re.split(r"\bcompare\b|\bversus\b|\bvs\.?\b|\band\b", lowered)
        for fragment in fragments:
            fragment = fragment.strip(" .,:;")
            if 2 <= len(fragment.split()) <= 5 and not any(fragment in item or item in fragment for item in targets):
                if not any(word in fragment for word in {"evaluate", "recommend", "limited", "technical", "staff"}):
                    targets.append(fragment)
    return _dedupe(targets)[:6]


def infer_query_dimensions(query: str) -> list[str]:
    lowered = normalize_label(query)
    dimensions = [label for label, terms in _DIMENSION_ALIASES.items() if any(term in lowered for term in terms)]
    if not dimensions:
        dimensions = ["reliability", "implementation cost", "maintainability"]
    return _dedupe(dimensions)[:8]


def build_evidence_criteria(original_query: str, planner_output: PlannerPrecontext) -> EvidenceCriteria:
    existing = planner_output.evidence_criteria
    targets = existing.comparison_targets or infer_query_targets(original_query)
    dimensions = existing.decision_dimensions or infer_query_dimensions(" ".join([original_query, *planner_output.coverage_checklist]))
    requirements = list(existing.coverage_requirements)
    if not requirements:
        for index, dimension in enumerate(dimensions, start=1):
            requirements.append(
                CoverageRequirement(
                    requirement_id=f"req_{index:02d}_{_slug(dimension)}",
                    label=dimension.title(),
                    description=f"Cover {dimension} for the relevant options in the user query.",
                    required_targets=targets,
                    required_dimensions=[dimension],
                )
            )
    preferred = existing.preferred_source_types or ["official", "paper", "docs", "academic", "benchmark", "primary"]
    terms = existing.source_fitness_terms or _dedupe([*targets, *dimensions, *_important_terms(original_query)])[:24]
    return EvidenceCriteria(
        comparison_targets=targets,
        decision_dimensions=dimensions,
        preferred_source_types=preferred,
        avoid_source_patterns=existing.avoid_source_patterns or ["unrelated domain", "marketing-only", "thin shell", "snippet only"],
        source_fitness_terms=terms,
        narrow_source_warnings=existing.narrow_source_warnings
        or ["single-vendor/tool evidence should not support broad category claims"],
        coverage_requirements=requirements,
    )


def score_source_fitness(
    original_query: str,
    planner_output: PlannerPrecontext,
    source: FetchedSource,
) -> dict[str, Any]:
    criteria = build_evidence_criteria(original_query, planner_output)
    haystack = normalize_label(" ".join([source.title or "", source.domain or "", source.url, source.text[:5000]]))
    query_terms = set(_important_terms(original_query))
    source_terms = set(_important_terms(haystack))
    notes: list[str] = []

    overlap = len(query_terms & source_terms) / max(1, min(len(query_terms), 18))
    target_hits = [target for target in criteria.comparison_targets if _label_hits(target, haystack)]
    dimension_hits = [dimension for dimension in criteria.decision_dimensions if _dimension_hits(dimension, haystack)]

    score = 0.20 + 0.35 * overlap
    score += min(0.25, 0.08 * len(target_hits))
    score += min(0.25, 0.06 * len(dimension_hits))
    if source.source_type in set(criteria.preferred_source_types):
        score += 0.12
        notes.append(f"preferred source type: {source.source_type}")
    if source.fetch_status == "arxiv_metadata_only":
        score -= 0.05
        notes.append("metadata-only source")
    if len((source.text or "").split()) < 120:
        score -= 0.18
        notes.append("thin source text")

    broad_query = len(criteria.comparison_targets) >= 2 or len(criteria.decision_dimensions) >= 4
    if broad_query and len(target_hits) <= 1 and len(dimension_hits) <= 1:
        score -= 0.20
        notes.append("narrow source for a broad comparison")
    if _looks_unrelated_to_query(original_query, haystack):
        score -= 0.25
        notes.append("domain appears weakly related to the user query")

    if target_hits:
        notes.append("covers target: " + ", ".join(target_hits[:3]))
    if dimension_hits:
        notes.append("covers dimension: " + ", ".join(dimension_hits[:3]))
    if not notes:
        notes.append("limited direct source-fit signal")

    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "target_hits": target_hits,
        "dimension_hits": dimension_hits,
        "notes": notes[:6],
    }


def score_evidence_fitness(planner_output: PlannerPrecontext, evidence: EvidenceItem) -> dict[str, Any]:
    criteria = planner_output.evidence_criteria
    text = normalize_label(" ".join([evidence.claim, evidence.source_quote, evidence.source_title]))
    target = evidence.target or _best_target(criteria.comparison_targets, text)
    dimension = evidence.dimension or _best_dimension(criteria.decision_dimensions, text)
    notes: list[str] = []

    score = max(evidence.relevance_to_query, 0.15)
    if target:
        score += 0.18
        notes.append(f"supports {target}")
    else:
        notes.append("no clear comparison target")
    if dimension:
        score += 0.18
        notes.append(f"covers {dimension}")
    else:
        notes.append("no clear decision dimension")
    if evidence.quote_location == "snippet":
        score = min(score, 0.45)
        notes.append("snippet-only evidence")
    if any("anchor_confidence" in note and not note.endswith("1.00") for note in evidence.limitations):
        score -= 0.05
    if "no information" in evidence.claim.lower():
        score = min(score, 0.35)
        notes.append("absence claim, use only as caveat")

    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "target": target,
        "dimension": dimension,
        "notes": notes[:5],
    }


def build_coverage_matrix(
    planner_output: PlannerPrecontext,
    evidence_items: list[EvidenceItem],
    fact_ledger: FactLedger | None = None,
) -> dict[str, Any]:
    criteria = planner_output.evidence_criteria
    targets = criteria.comparison_targets or ["overall"]
    dimensions = criteria.decision_dimensions or planner_output.coverage_checklist or ["overall"]
    matrix: dict[str, dict[str, dict[str, Any]]] = {
        target: {
            dimension: {"evidence_ids": [], "fact_ids": [], "score": 0.0, "status": "missing", "notes": []}
            for dimension in dimensions
        }
        for target in targets
    }

    evidence_by_id = {item.evidence_id: item for item in evidence_items}
    fact_by_evidence: dict[str, list[str]] = {}
    if fact_ledger:
        for fact in [*fact_ledger.verified_facts, *fact_ledger.partial_facts]:
            for evidence_id in fact.supporting_evidence_ids:
                fact_by_evidence.setdefault(evidence_id, []).append(fact.fact_id)

    for item in evidence_items:
        fit = score_evidence_fitness(planner_output, item)
        target = _canonical_target(item.target or fit["target"], targets) or _nearest(targets)
        dimension = _canonical_dimension(item.dimension or fit["dimension"], dimensions) or _nearest(dimensions)
        if target not in matrix:
            target = _nearest(targets)
        if dimension not in matrix[target]:
            dimension = _nearest(dimensions)
        cell = matrix[target][dimension]
        cell["evidence_ids"].append(item.evidence_id)
        cell["fact_ids"].extend(fact_by_evidence.get(item.evidence_id, []))
        cell["score"] = round(max(float(cell["score"]), float(item.evidence_fit_score or fit["score"])), 3)
        cell["status"] = "strong" if cell["score"] >= 0.72 else "weak"
        cell["notes"].extend((item.evidence_fit_notes or fit["notes"])[:2])

    missing = []
    weak = []
    strong = []
    for target, rows in matrix.items():
        for dimension, cell in rows.items():
            cell["fact_ids"] = _dedupe(cell["fact_ids"])
            cell["notes"] = _dedupe(cell["notes"])[:4]
            label = {"target": target, "dimension": dimension, "status": cell["status"], "score": cell["score"]}
            if cell["status"] == "missing":
                missing.append(label)
            elif cell["status"] == "weak":
                weak.append(label)
            else:
                strong.append(label)

    average = 0.0
    cells = [cell for rows in matrix.values() for cell in rows.values()]
    if cells:
        average = round(sum(float(cell["score"]) for cell in cells) / len(cells), 3)
    return {
        "targets": targets,
        "dimensions": dimensions,
        "matrix": matrix,
        "summary": {
            "average_evidence_fit": average,
            "missing_requirements": missing,
            "weak_requirements": weak,
            "strong_requirements": strong,
            "evidence_item_count": len(evidence_by_id),
        },
    }


def _canonical_target(value: str, targets: list[str]) -> str:
    text = normalize_label(value)
    if not text:
        return ""
    for target in targets:
        if normalize_label(target) == text:
            return target
    for target in targets:
        target_text = normalize_label(target)
        if target_text in text or text in target_text:
            return target
    alias_groups = {
        "retrieval-augmented chatbot": {"rag", "rag chatbot", "rag chatbots", "retrieval augmented", "retrieval-augmented"},
        "general-purpose chatbot": {"general chatbot", "general chatbots", "general purpose", "chatgpt", "claude"},
        "source-audited research workflow": {"source audited", "source-audited", "audit-ready", "audited workflow"},
    }
    for canonical, aliases in alias_groups.items():
        if canonical in targets and any(alias in text for alias in aliases):
            return canonical
    return ""


def _canonical_dimension(value: str, dimensions: list[str]) -> str:
    text = normalize_label(value)
    if not text:
        return ""
    for dimension in dimensions:
        if normalize_label(dimension) == text:
            return dimension
    for dimension in dimensions:
        if _dimension_hits(dimension, text):
            return dimension
    return ""


def _best_target(targets: list[str], text: str) -> str:
    for target in targets:
        if _label_hits(target, text):
            return target
    return ""


def _best_dimension(dimensions: list[str], text: str) -> str:
    for dimension in dimensions:
        if _dimension_hits(dimension, text):
            return dimension
    return ""


def _dimension_hits(dimension: str, text: str) -> bool:
    terms = _DIMENSION_ALIASES.get(normalize_label(dimension), {normalize_label(dimension)})
    return any(term in text for term in terms)


def _label_hits(label: str, text: str) -> bool:
    label = normalize_label(label)
    if label in text:
        return True
    return bool(set(_important_terms(label)) & set(_important_terms(text)))


def _looks_unrelated_to_query(query: str, text: str) -> bool:
    q_terms = set(_important_terms(query))
    t_terms = set(_important_terms(text))
    if not q_terms:
        return False
    return len(q_terms & t_terms) / max(1, min(len(q_terms), 18)) < 0.08


def _important_terms(text: str) -> list[str]:
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "into", "should", "would",
        "compare", "evaluate", "recommend", "best", "safest", "architecture", "workflow",
        "limited", "technical", "staff", "small", "long", "term",
    }
    return _dedupe([term for term in re.findall(r"[a-z0-9]+", normalize_label(text)) if len(term) > 2 and term not in stop])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize_label(value)).strip("_") or "coverage"


def _nearest(values: list[str]) -> str:
    return values[0] if values else "overall"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        key = normalize_label(str(value))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(value).strip())
    return out
