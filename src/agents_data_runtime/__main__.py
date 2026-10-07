#!/usr/bin/env python3
"""Composition root for the agent communication runtime."""

from __future__ import annotations




from . import Application
from shared.get_config import get_config
def run():
    app = Application(get_config())
    app.install_agent("/home/user-system/repositories/agents-system/agents/cccp")
    return 0
if __name__ == "__main__":
    raise SystemExit(run())
