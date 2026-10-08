#!/usr/bin/env python3
"""Composition root for the local agents_data application."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "agents_data"

from .app.application import main


if __name__ == "__main__":
    raise SystemExit(main())
