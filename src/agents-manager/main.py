#!/usr/bin/env python3
"""Standalone entrypoint for Agents Manager."""

from __future__ import annotations

import sys
from pathlib import Path


APPLICATION_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = APPLICATION_ROOT.parent
for path in (APPLICATION_ROOT, SOURCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application import AgentApplication  # noqa: E402
from shared.get_config import get_config  # noqa: E402


def main() -> int:
    return AgentApplication(get_config()).run()


if __name__ == "__main__":
    raise SystemExit(main())
