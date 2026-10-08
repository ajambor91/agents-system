#!/usr/bin/env python3
"""Render a local resources/app_env.json for system or dev test values."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_scripts.common import RenderError  # noqa: E402
from internal_scripts.render_app_env import render  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="test_render_env")
    mode = value.add_mutually_exclusive_group(required=True)
    mode.add_argument("--system", action="store_const", const="system", dest="mode")
    mode.add_argument("--dev", action="store_const", const="dev", dest="mode")
    value.add_argument("-v", "--verbose", action="store_true")
    return value


def render_local_environment(
    mode: str,
    *,
    project_root: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Overwrite only the local resources/app_env.json."""
    root = (project_root or Path(__file__).resolve().parents[2]).resolve()
    return render(
        mode=mode,
        package_dir=root,
        install_dir=root,
        output=root / "resources" / "app_env.json",
        force=True,
        environment=os.environ,
        value_resolver=lambda _name: None,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        result = render_local_environment(arguments.mode, verbose=arguments.verbose)
    except RenderError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

