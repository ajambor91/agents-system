"""Command boundary model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiResult:
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
