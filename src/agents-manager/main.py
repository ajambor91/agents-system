#!/usr/bin/env python3

import sys
from pathlib import Path

APPLICATION_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = APPLICATION_ROOT.parent
for path in (APPLICATION_ROOT, SOURCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.application import AgentApplication


def main() -> int:
    return AgentApplication.instance().run()


def create_service():
    """Expose a resident health handler; normal agents CLI remains unchanged."""
    def handle(payload: dict) -> dict:
        action = str(payload.get("action", "health"))
        if action != "health":
            raise ValueError("agents-manager runtime obsługuje obecnie tylko health")
        return {"status": "ready", "service": "agents-manager"}

    return handle


if __name__ == "__main__":
    raise SystemExit(main())