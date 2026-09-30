#!/usr/bin/env python3
"""Composition root for the agent communication runtime."""

from __future__ import annotations

import sys
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = APPLICATION_ROOT.parent
for path in (APPLICATION_ROOT, SOURCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from service import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
