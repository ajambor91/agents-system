#!/usr/bin/env python3
"""Composition root for the agent communication runtime."""

from __future__ import annotations




from .app import Application
from .runtime.runtime import Runtime
from shared.get_config import get_config
def run():
    config = get_config()
    app = Application(config)
    # res = app.install_agent("/home/user-system/repositories/agents-system/agents/www")
    # res =  app.remove_agent('www')
    # res = app.run_agent("www", "Powiedz cokolwiek")
    # print(res)
    runtime = Runtime(configuration=config, app=app)
    runtime.run()
    return 0
if __name__ == "__main__":
    raise SystemExit(run())
