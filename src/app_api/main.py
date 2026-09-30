#!/usr/bin/env python3
"""Public and resident entrypoint for the Agents System console API."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from app_api.app.application import Application  # noqa: E402
from app_api.app.models import ApiResult  # noqa: E402


def execute(
    arguments: Sequence[str] | None = None,
    *,
    application: Application | None = None,
) -> ApiResult:
    argv = list(sys.argv[1:] if arguments is None else arguments)
    return (application or Application()).run(argv)


def emit(result: ApiResult) -> int:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.exit_code


def main(arguments: Sequence[str] | None = None) -> int:
    return emit(execute(arguments))


def create_service():
    application = Application()

    def handle(payload: dict[str, Any]) -> dict[str, Any]:
        raw = payload.get("args", [])
        if not isinstance(raw, list):
            return ApiResult(exit_code=2, stderr="Błąd: args musi być tablicą\n").to_dict()
        return application.run([str(item) for item in raw], use_runtime=False).to_dict()

    return handle


if __name__ == "__main__":
    raise SystemExit(main())
