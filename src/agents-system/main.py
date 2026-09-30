#!/usr/bin/env python3
"""Canonical JSON-driven Agents System entrypoint at its fixed application path."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

APPLICATION_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = APPLICATION_ROOT.parent
for path in (APPLICATION_ROOT, SOURCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application import Application  # noqa: E402
from app.errors import AgentsSystemError  # noqa: E402
from app.models import CommandResult  # noqa: E402


def execute(arguments: Sequence[str] | None = None, *, application: Application | None = None) -> CommandResult:
    try:
        return (application or Application()).run(list(sys.argv[1:] if arguments is None else arguments))
    except AgentsSystemError as exc:
        return CommandResult(exit_code=exc.exit_code, stderr=f"Błąd: {exc}\n")
    except KeyboardInterrupt:
        return CommandResult(exit_code=130, stderr="Błąd: przerwano przez użytkownika\n")
    except OSError as exc:
        return CommandResult(exit_code=1, stderr=f"Błąd systemowy: {exc}\n")


def emit(result: CommandResult) -> int:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.exit_code


def main(arguments: Sequence[str] | None = None) -> int:
    return emit(execute(arguments))


def create_service():
    """Expose the same Application.execute path to the resident runtime."""
    application = Application()

    def handle(payload: dict[str, Any]) -> dict[str, Any]:
        raw = payload.get("args", [])
        if not isinstance(raw, list):
            return {"handled": True, "exit_code": 2, "stderr": "Błąd: args musi być tablicą.\n"}
        command = str(payload.get("command", ""))
        result = application.run([command, *[str(item) for item in raw]])
        return {"handled": True, **result.to_dict()}

    return handle


if __name__ == "__main__":
    raise SystemExit(main())
