from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation failure, with a fully qualified path from its model."""

    path: str
    error: Exception

    @property
    def message(self) -> str:
        return str(self.error)

    def with_prefix(self, prefix: str) -> ValidationIssue:
        separator = "." if self.path else ""
        return ValidationIssue(f"{prefix}{separator}{self.path}", self.error)

    def __str__(self) -> str:
        return f"{self.path}: {type(self.error).__name__}: {self.error}"