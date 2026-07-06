"""Port: access to uploaded datasets (the datasets bucket)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DatasetStorage(ABC):
    """Storage-agnostic boundary for dataset upload and existence checks."""

    @abstractmethod
    def generate_upload_url(self, key: str, *, expires_in_seconds: int) -> str:
        """Return a time-limited URL the client can PUT a dataset to."""

    @abstractmethod
    def get_size(self, key: str) -> int | None:
        """Return the object's size in bytes, or None if it doesn't exist."""
