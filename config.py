import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    GOLDEN_RESULT_PATH: str = os.getenv("GOLDEN_RESULT_PATH", "tests/fixtures/demo_golden.json")
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo,arxiv")
    DDGS_REGION: str = os.getenv("DDGS_REGION", "wt-wt")
    DDGS_SAFESEARCH: str = os.getenv("DDGS_SAFESEARCH", "moderate")
    DDGS_TIMEOUT_SECONDS: float = float(os.getenv("DDGS_TIMEOUT_SECONDS", "15"))
    ARXIV_MAX_RESULTS: int = int(os.getenv("ARXIV_MAX_RESULTS", "5"))
    ARXIV_TIMEOUT_SECONDS: float = float(os.getenv("ARXIV_TIMEOUT_SECONDS", "10"))
    SOURCE_FETCH_ENABLED: bool = os.getenv("SOURCE_FETCH_ENABLED", "true").lower() in {"1", "true", "yes"}
    SOURCE_FETCH_TIMEOUT_SECONDS: float = float(os.getenv("SOURCE_FETCH_TIMEOUT_SECONDS", "20"))
    SOURCE_FETCH_MAX_CHARS: int = int(os.getenv("SOURCE_FETCH_MAX_CHARS", "12000"))
    SOURCE_FETCH_HTTP_FIRST: bool = os.getenv("SOURCE_FETCH_HTTP_FIRST", "true").lower() in {"1", "true", "yes"}
    SOURCE_FETCH_MIN_TEXT_CHARS: int = int(os.getenv("SOURCE_FETCH_MIN_TEXT_CHARS", "500"))
    CAMOFOX_ENABLED: bool = os.getenv("CAMOFOX_ENABLED", "false").lower() in {"1", "true", "yes"}
    CAMOFOX_BASE_URL: str = os.getenv("CAMOFOX_BASE_URL", "http://localhost:9377")
    CAMOFOX_HEALTH_PATH: str = os.getenv("CAMOFOX_HEALTH_PATH", "/health")
    CAMOFOX_FETCH_PATH: str = os.getenv("CAMOFOX_FETCH_PATH", "")
    CAMOFOX_TIMEOUT_SECONDS: float = float(os.getenv("CAMOFOX_TIMEOUT_SECONDS", "30"))
    CAMOFOX_SCREENSHOT: bool = os.getenv("CAMOFOX_SCREENSHOT", "false").lower() in {"1", "true", "yes"}
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_BASE_URL: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    OPENCODE_GO_API_KEY: str = os.getenv("OPENCODE_GO_API_KEY", "")
    OPENCODE_GO_BASE_URL: str = os.getenv("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1")
    OPENCODE_GO_MODEL: str = os.getenv("OPENCODE_GO_MODEL", "qwen3.6-plus")
    OPENCODE_GO_AUTH_HEADER: str = os.getenv("OPENCODE_GO_AUTH_HEADER", "Authorization")
    OPENCODE_GO_AUTH_SCHEME: str = os.getenv("OPENCODE_GO_AUTH_SCHEME", "Bearer")
    SYNTHESIZER_PROVIDER: str = os.getenv("SYNTHESIZER_PROVIDER", "")
    SYNTHESIZER_MODEL: str = os.getenv("SYNTHESIZER_MODEL", "")
    SYNTHESIZER_MAX_TOKENS: int = int(os.getenv("SYNTHESIZER_MAX_TOKENS", "64000"))
    SYNTHESIZER_REASONING_EFFORT: str = os.getenv("SYNTHESIZER_REASONING_EFFORT", "high")
    SYNTHESIZER_TEMPERATURE: float = float(os.getenv("SYNTHESIZER_TEMPERATURE", "0.2"))
    EXTRACTION_MAX_TOKENS: int = int(os.getenv("EXTRACTION_MAX_TOKENS", "64000"))
    EXTRACTION_REASONING_EFFORT: str = os.getenv("EXTRACTION_REASONING_EFFORT", "high")
    EXTRACTION_MAX_CONCURRENT_CALLS: int = int(os.getenv("EXTRACTION_MAX_CONCURRENT_CALLS", "4"))
    RUN_LIVE_SEARCH_TESTS: bool = os.getenv("RUN_LIVE_SEARCH_TESTS", "false").lower() in {"1", "true", "yes"}
    RUN_LIVE_LLM_TESTS: bool = os.getenv("RUN_LIVE_LLM_TESTS", "false").lower() in {"1", "true", "yes"}
    RUN_CAMOFOX_TESTS: bool = os.getenv("RUN_CAMOFOX_TESTS", "false").lower() in {"1", "true", "yes"}
    MAX_SEARCH_HEADERS_TOTAL: int = int(os.getenv("MAX_SEARCH_HEADERS_TOTAL", "20"))
    MAX_FETCHED_SOURCES_TOTAL: int = int(os.getenv("MAX_FETCHED_SOURCES_TOTAL", "10"))
    SOURCE_CONTEXT_TOKENS: int = int(os.getenv("SOURCE_CONTEXT_TOKENS", "2000"))
    SOURCE_DEEP_REVIEW_TOKENS: int = int(os.getenv("SOURCE_DEEP_REVIEW_TOKENS", "20000"))
    LLM_MAX_CONCURRENT_CALLS: int = int(os.getenv("LLM_MAX_CONCURRENT_CALLS", "1"))
    LLM_STAGE_TIMEOUT_SECONDS: float = float(os.getenv("LLM_STAGE_TIMEOUT_SECONDS", "120"))
    ENABLE_DEEP_SOURCE_REVIEW: bool = os.getenv("ENABLE_DEEP_SOURCE_REVIEW", "true").lower() in {"1", "true", "yes"}
    CONFIDENCE_VERIFIED_WEIGHT: float = float(os.getenv("CONFIDENCE_VERIFIED_WEIGHT", "0.40"))
    CONFIDENCE_SOURCE_QUALITY_WEIGHT: float = float(os.getenv("CONFIDENCE_SOURCE_QUALITY_WEIGHT", "0.20"))
    CONFIDENCE_AGREEMENT_WEIGHT: float = float(os.getenv("CONFIDENCE_AGREEMENT_WEIGHT", "0.20"))
    CONFIDENCE_RECENCY_WEIGHT: float = float(os.getenv("CONFIDENCE_RECENCY_WEIGHT", "0.10"))
    CONFIDENCE_COVERAGE_WEIGHT: float = float(os.getenv("CONFIDENCE_COVERAGE_WEIGHT", "0.10"))

    # --- Phase 0.2: demo query override (kept general for any program) ---
    DEMO_QUERY: str = os.getenv(
        "DEMO_QUERY",
        (
            "What are the strongest evidence-backed approaches for building a trustworthy "
            "AI research assistant for students, researchers, and builders?"
        ),
    )

    # --- Phase 1.1: Gemini reasoning controls (optional; empty = preserve current behavior) ---
    GEMINI_THINKING_BUDGET: str = os.getenv("GEMINI_THINKING_BUDGET", "")
    GEMINI_INCLUDE_THOUGHTS: bool = os.getenv("GEMINI_INCLUDE_THOUGHTS", "false").lower() in {"1", "true", "yes"}

    # --- Phase 1.2: per-stage model overrides (empty = use GEMINI_MODEL / LLM_PROVIDER default) ---
    PLANNER_PROVIDER: str = os.getenv("PLANNER_PROVIDER", "")
    PLANNER_MODEL: str = os.getenv("PLANNER_MODEL", "")
    EXTRACTION_PROVIDER: str = os.getenv("EXTRACTION_PROVIDER", "")
    EXTRACTION_MODEL: str = os.getenv("EXTRACTION_MODEL", "")
    FACT_CHECKER_PROVIDER: str = os.getenv("FACT_CHECKER_PROVIDER", "")
    FACT_CHECKER_MODEL: str = os.getenv("FACT_CHECKER_MODEL", "")
    COVERAGE_AUDITOR_PROVIDER: str = os.getenv("COVERAGE_AUDITOR_PROVIDER", "")
    COVERAGE_AUDITOR_MODEL: str = os.getenv("COVERAGE_AUDITOR_MODEL", "")

    # --- Phase 1.4: fact-checker tuning ---
    FACT_CHECKER_SUPPORT_THRESHOLD: float = float(os.getenv("FACT_CHECKER_SUPPORT_THRESHOLD", "0.72"))
    FACT_CHECKER_LLM_RETRY_ON_EMPTY: bool = os.getenv("FACT_CHECKER_LLM_RETRY_ON_EMPTY", "true").lower() in {"1", "true", "yes"}

    # --- Phase 2.1: gap-filling loop (1 = current one-shot behavior) ---
    MAX_RESEARCH_ITERATIONS: int = int(os.getenv("MAX_RESEARCH_ITERATIONS", "1"))

    # --- Phase 3: Gemini-native capability flags (default off to preserve behavior) ---
    GEMINI_GROUNDING_ENABLED: bool = os.getenv("GEMINI_GROUNDING_ENABLED", "false").lower() in {"1", "true", "yes"}
    MULTIMODAL_ENABLED: bool = os.getenv("MULTIMODAL_ENABLED", "false").lower() in {"1", "true", "yes"}
    LIVE_TOOL_AGENT_ENABLED: bool = os.getenv("LIVE_TOOL_AGENT_ENABLED", "false").lower() in {"1", "true", "yes"}

    # --- Semantic reranker (FlashRank): second-stage filter over search headers ---
    # Default OFF so the existing lexical-only reranker behavior is preserved.
    # When enabled, a cross-encoder score (normalized to [0,1]) is blended into
    # the lexical score via SEMANTIC_RERANK_WEIGHT. Delete this module + these
    # envs to fully remove the feature.
    SEMANTIC_RERANK_ENABLED: bool = os.getenv("SEMANTIC_RERANK_ENABLED", "false").lower() in {"1", "true", "yes"}
    SEMANTIC_RERANK_MODEL: str = os.getenv("SEMANTIC_RERANK_MODEL", "ms-marco-MiniLM-L-12-v2")
    SEMANTIC_RERANK_WEIGHT: float = float(os.getenv("SEMANTIC_RERANK_WEIGHT", "2.0"))
    # Headers scored below this semantic threshold are dropped outright when the
    # reranker is enabled and produced a score for them. 0.0 disables the floor.
    # Applied only in combination with SEMANTIC_RERANK_ENABLED; no effect
    # otherwise.
    SEMANTIC_RERANK_MIN_SCORE: float = float(os.getenv("SEMANTIC_RERANK_MIN_SCORE", "0.01"))

    @classmethod
    def active_llm_summary(cls) -> dict[str, str]:
        """Return a provider-aware snapshot suitable for UI sidebars.

        Reads the active provider from ``LLM_PROVIDER`` and picks the matching
        ``*_MODEL`` / ``*_BASE_URL`` trio. Falls back to safe blanks when a
        provider is misconfigured so the UI never crashes with AttributeError.
        """
        provider = (cls.LLM_PROVIDER or "").lower().strip() or "none"
        if provider == "gemini":
            return {
                "provider": "gemini",
                "model": cls.GEMINI_MODEL,
                "endpoint": cls.GEMINI_BASE_URL,
            }
        if provider == "opencode_go":
            return {
                "provider": "opencode_go",
                "model": cls.OPENCODE_GO_MODEL,
                "endpoint": cls.OPENCODE_GO_BASE_URL,
            }
        return {"provider": provider, "model": "", "endpoint": ""}


config = Config()
