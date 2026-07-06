"""JobId: the platform's one correlation key end to end (see ADR-0008)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ulid import ULID

_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


@dataclass(frozen=True, slots=True)
class JobId:
    """A validated ULID identifying one batch inference job."""

    value: str

    def __post_init__(self) -> None:
        if not _ULID_PATTERN.match(self.value):
            raise ValueError(f"'{self.value}' is not a valid ULID job id")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> JobId:
        """Create a new, time-sortable job id."""
        return cls(str(ULID()))
