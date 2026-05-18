"""OpenCode Go LLM provider wrapper."""

from config import config
from backend.providers.llm.openai_compatible import OpenAICompatibleProvider


class OpenCodeGoProvider(OpenAICompatibleProvider):
    def __init__(self, **kwargs):
        super().__init__(
            base_url=kwargs.pop("base_url", config.OPENCODE_GO_BASE_URL),
            model=kwargs.pop("model", config.OPENCODE_GO_MODEL),
            api_key=kwargs.pop("api_key", config.OPENCODE_GO_API_KEY),
            provider="opencode_go",
            auth_header=kwargs.pop("auth_header", config.OPENCODE_GO_AUTH_HEADER),
            auth_scheme=kwargs.pop("auth_scheme", config.OPENCODE_GO_AUTH_SCHEME),
            timeout_seconds=kwargs.pop("timeout_seconds", config.LLM_TIMEOUT_SECONDS),
            **kwargs,
        )
