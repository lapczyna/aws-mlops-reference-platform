"""Port: access to prediction outputs (the results bucket)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ResultsStorage(ABC):
    """Storage-agnostic boundary for retrieving prediction outputs."""

    @abstractmethod
    def generate_download_url(self, key: str, *, expires_in_seconds: int) -> str:
        """Return a time-limited URL the client can download predictions from."""
