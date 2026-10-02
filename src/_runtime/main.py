#!/usr/bin/env python3
"""Dedicated entrypoint for the shared resident runtime process."""

import sys
from pathlib import Path

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = SCRIPT_DIR.parent

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
from _runtime.app.runtime_app import RuntimeApp
from _runtime.app.main_runtime import MainRuntime

def get_env() -> None:
    script_dir = Path(__file__).resolve().parent
    env_file = (script_dir / "./../.env").resolve()

    if not env_file.is_file():
        raise FileNotFoundError(f"Environment file not found: {env_file}")

    load_dotenv(env_file)


def main() -> int:
    """Run the shared resident runtime process."""

    get_env()

    bootstrap = RuntimeApp()
    data_class = bootstrap.get_data()
    direct_runtime = MainRuntime(data_class.instance_manager, data_class.configuration)
    direct_runtime.run()
    del bootstrap
    del data_class
    return 0


if __name__ == "__main__":
    raise SystemExit(main())