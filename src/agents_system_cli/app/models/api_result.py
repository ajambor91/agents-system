"""Boundary models owned by the agents_system_cli application layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiResult:
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
