"""Process and runtime adapters used by the console boundary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..models import ApiError


class ControlPlaneClient:
    """Forward one validated envelope to the canonical Agents System command."""

    def __init__(self, repository_root: Path) -> None:
        self.entrypoint = repository_root / "src" / "agents-system" / "main.py"

    def dispatch(self, envelope: dict[str, Any]) -> dict[str, Any]:
        completed = subprocess.run(
            [
                sys.executable,
                str(self.entrypoint),
                "console-dispatch",
                "--request",
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":")),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "Błąd control plane"
            raise ApiError(message, exit_code=completed.returncode)
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ApiError("Control plane zwrócił nieprawidłowy JSON", exit_code=1) from exc
        if not isinstance(response, dict):
            raise ApiError("Control plane zwrócił nieprawidłową odpowiedź", exit_code=1)
        return response

