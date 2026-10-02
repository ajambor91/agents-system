#!/usr/bin/env python3
"""Render local test JSON documents and regenerate library Configuration."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_scripts.common import RenderError  # noqa: E402
from internal_scripts.generate_configuration import generate  # noqa: E402
from internal_scripts.test_render_env import render_local_environment  # noqa: E402
from internal_scripts.test_render_modules import render_local_modules  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="test_set_configuration")
    mode = value.add_mutually_exclusive_group(required=True)
    mode.add_argument("--system", action="store_const", const="system", dest="mode")
    mode.add_argument("--dev", action="store_const", const="dev", dest="mode")
    value.add_argument("-v", "--verbose", action="store_true")
    return value


def set_local_configuration(mode: str, *, verbose: bool = False) -> dict[str, str]:
    """Run both local renderers and then regenerate configuration.py."""
    root = Path(__file__).resolve().parents[2]
    environment = render_local_environment(mode, project_root=root, verbose=verbose)
    modules = render_local_modules(mode, project_root=root, verbose=verbose)
    source = root / "resources" / "app_env.json"
    target = root / "src" / "lib" / "configuration" / "configuration.py"
    with contextlib.redirect_stdout(io.StringIO()):
        generate(source)
    if not target.is_file():
        raise RenderError(f"Generator nie utworzył pliku: {target}")
    return {
        "mode": mode,
        "environment": environment["output"],
        "modules": modules["output"],
        "configuration": str(target.resolve()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        result = set_local_configuration(arguments.mode, verbose=arguments.verbose)
    except (OSError, ValueError, TypeError, RenderError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

