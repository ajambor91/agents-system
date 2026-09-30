"""Immutable command boundary models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CommandRequest:
    """Validated request passed by Command to Application."""

    command: str
    arguments: dict[str, Any]
    sources: dict[str, str]
    actor: dict[str, Any]
    request_id: str


@dataclass(slots=True)
class CommandResult:
    """Structured application result rendered only by the CLI boundary."""

    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "data": self.data,
        }
