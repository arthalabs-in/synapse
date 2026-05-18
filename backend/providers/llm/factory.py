"""LLM provider factory."""

from config import config
from backend.providers.llm.gemini import GeminiProvider
from backend.providers.llm.opencode_go import OpenCodeGoProvider


# Phase 1.2: per-stage env mapping. Empty values fall back to the global
# LLM_PROVIDER / GEMINI_MODEL defaults so existing users get today's behavior.
_STAGE_ENV_MAP: dict[str, tuple[str, str]] = {
    "synthesizer": ("SYNTHESIZER_PROVIDER", "SYNTHESIZER_MODEL"),
    "planner": ("PLANNER_PROVIDER", "PLANNER_MODEL"),
    "extraction": ("EXTRACTION_PROVIDER", "EXTRACTION_MODEL"),
    "fact_checker": ("FACT_CHECKER_PROVIDER", "FACT_CHECKER_MODEL"),
    "coverage_auditor": ("COVERAGE_AUDITOR_PROVIDER", "COVERAGE_AUDITOR_MODEL"),
}


def create_llm_provider(stage: str | None = None):
    provider = _provider_for_stage(stage)
    model = _model_for_stage(stage, provider)
    kwargs = _provider_kwargs_for_stage(stage)
    if provider == "gemini":
        return GeminiProvider(model=model or config.GEMINI_MODEL, **kwargs)
    if provider == "opencode_go":
        return OpenCodeGoProvider(model=model or config.OPENCODE_GO_MODEL, **kwargs)
    raise ValueError(f"unsupported LLM_PROVIDER: {config.LLM_PROVIDER}")


def _provider_for_stage(stage: str | None) -> str:
    env_pair = _STAGE_ENV_MAP.get(stage or "")
    if env_pair:
        provider_attr = env_pair[0]
        override = getattr(config, provider_attr, "") or ""
        if override:
            return override.lower()
    return config.LLM_PROVIDER.lower()


def _model_for_stage(stage: str | None, provider: str) -> str:
    env_pair = _STAGE_ENV_MAP.get(stage or "")
    if env_pair:
        model_attr = env_pair[1]
        override = getattr(config, model_attr, "") or ""
        if override:
            return override
    if provider == "gemini":
        return config.GEMINI_MODEL
    if provider == "opencode_go":
        return config.OPENCODE_GO_MODEL
    return ""


def _provider_kwargs_for_stage(stage: str | None) -> dict:
    if stage == "extraction":
        return {"max_concurrent_calls": config.EXTRACTION_MAX_CONCURRENT_CALLS}
    return {}
