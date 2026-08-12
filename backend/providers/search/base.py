"""Search provider interface."""

from typing import Protocol

from backend.models import SearchHeader


class SearchProviderError(RuntimeError):
    """Raised when a search provider cannot return results."""


class SearchProvider(Protocol):
    async def search(self, query: str, max_results: int = 5, **kwargs) -> list[SearchHeader]:
        """Return search headers only. Headers are not evidence."""
