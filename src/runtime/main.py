#!/usr/bin/env python3
"""Dedicated entrypoint for the shared resident runtime process."""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from runtime.service import RuntimeErrorMessage, configure, serve  # noqa: E402
from shared.configuration import ApplicationEnvironment  # noqa: E402


def main() -> int:
    try:
        configure(ApplicationEnvironment.discover(SOURCE_ROOT.parent))
        return serve()
    except RuntimeErrorMessage as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
