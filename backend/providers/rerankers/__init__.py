"""Optional semantic rerankers for SYNAPSE search pipeline.

Additive package. Delete this directory (plus the ``SEMANTIC_RERANK_*``
entries in ``config.py`` / ``.env.example`` and the import in
``backend/reranker.py``) to fully remove the feature.
"""

from backend.providers.rerankers.flashrank_reranker import (
    FlashRankSemanticReranker,
    get_default_semantic_reranker,
)

__all__ = ["FlashRankSemanticReranker", "get_default_semantic_reranker"]
