#!/usr/bin/env python3
"""Render a local resources/agents-system.module.json from local environment data."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_scripts.common import RenderError, load_object  # noqa: E402
from internal_scripts.render_modules_manifest import render  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="test_render_modules")
    mode = value.add_mutually_exclusive_group(required=True)
    mode.add_argument("--system", action="store_const", const="system", dest="mode")
    mode.add_argument("--dev", action="store_const", const="dev", dest="mode")
    value.add_argument("-v", "--verbose", action="store_true")
    return value


def _environment_values(path: Path) -> dict[str, str]:
    document = load_object(path)
    if (
        document.get("schema_version") != 1
        or document.get("kind") != "agents-system-environment"
    ):
        raise RenderError(f"Nieprawidłowy lokalny app_env.json: {path}")
    variables = document.get("variables")
    if not isinstance(variables, list):
        raise RenderError(f"app_env.json nie zawiera tablicy variables: {path}")
    values: dict[str, str] = {}
    for offset, item in enumerate(variables):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("value"), str)
        ):
            raise RenderError(f"app_env.json variables[{offset}] ma nieprawidłowy format")
        name = item["name"]
        if name in values:
            raise RenderError(f"Powtórzona zmienna w app_env.json: {name}")
        values[name] = item["value"]
    return values


def render_local_modules(
    mode: str,
    *,
    project_root: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Overwrite only the local resources/agents-system.module.json."""
    root = (project_root or Path(__file__).resolve().parents[2]).resolve()
    environment_path = root / "resources" / "app_env.json"
    values = _environment_values(environment_path)
    rendered_mode = values.get("INSTALL_MODE")
    if rendered_mode != mode:
        raise RenderError(
            f"Lokalny app_env.json ma INSTALL_MODE={rendered_mode!r}; "
            f"najpierw uruchom test_render_env --{mode}"
        )

    output = root / "resources" / "agents-system.module.json"
    return render(
        package_dir=root,
        app_dir=root,
        modules_dir=root / "src",
        manifest_path=output,
        output=output,
        force=True,
        verbose=verbose,
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        result = render_local_modules(arguments.mode, verbose=arguments.verbose)
    except RenderError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

