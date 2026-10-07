#!/usr/bin/env python3
"""Render and validate resources/agents-system.module.template.json."""

from __future__ import annotations

import logging


import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manifests import ManifestsApp
from internal_scripts.common import (  # noqa: E402
    SAFE_IDENTIFIER,
    SHELL_REFERENCE,
    RenderError,
    atomic_json,
    is_below,
    load_object,
    require_absolute_directory,
)


REQUIRED_CHILD_FIELDS = {
    "module_name",
    "section_name",
    "absolute_module_path",
    "is_menu_option",
    "is_runtime",
    "runtime",
    "manifest_path",
}
SECTION_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


from lib.logging_config import configure_logging


LOGGER = logging.getLogger(__name__)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="render-modules-manifest")
    value.add_argument("-a", "--app-dir", required=True)
    value.add_argument("-d", "--modules-dir", required=True)
    value.add_argument("-m", "--manifest-path", required=True)
    value.add_argument("-o", "--output")
    value.add_argument("-f", "--force", action="store_true")
    value.add_argument("-v", "--verbose", action="store_true")
    return value


def _absolute_file(value: Path | str, name: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise RenderError(f"{name} musi być bezpieczną ścieżką absolutną")
    return candidate.resolve(strict=False)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _validate_command(module_name: str, command: Any, offset: int) -> None:
    if not isinstance(command, dict):
        raise RenderError(f"{module_name}.commands[{offset}] musi być obiektem")
    name = command.get("name")
    if not isinstance(name, str) or not SAFE_IDENTIFIER.fullmatch(name):
        raise RenderError(f"{module_name}.commands[{offset}].name jest nieprawidłowe")
    for field in ("description", "usage"):
        if not isinstance(command.get(field), str) or not command[field].strip():
            raise RenderError(f"{module_name}.{name}.{field} musi być niepustym tekstem")
    if not isinstance(command.get("flags"), list):
        raise RenderError(f"{module_name}.{name}.flags musi być tablicą")


def render(
    *,
    package_dir: Path,
    app_dir: Path,
    modules_dir: Path,
    manifest_path: Path,
    output: Path,
    force: bool,
    verbose: bool = False,
) -> dict[str, Any]:
    package = require_absolute_directory(str(package_dir), "APPLICATION_ROOT")
    application = require_absolute_directory(str(app_dir), "APP_DIR")
    modules = require_absolute_directory(str(modules_dir), "MODULES_DIR")
    installed_manifest = _absolute_file(manifest_path, "MODULES_MANIFEST_PATH")
    template = load_object(package / "resources" / "agents-system.module.template.json")
    if (
        template.get("schema_version") != 1
        or template.get("kind") != "agents-system-modules-manifest"
    ):
        raise RenderError(
            "agents-system.module.template.json wymaga schema_version=1 "
            "i kind=agents-system-modules-manifest"
        )
    app_module_name = template.get("app_module_name")
    if not isinstance(app_module_name, str) or not SAFE_IDENTIFIER.fullmatch(app_module_name):
        raise RenderError("app_module_name musi być bezpiecznym identyfikatorem")
    children = template.get("children")
    if not isinstance(children, list) or not children:
        raise RenderError("agents-system.module.template.json: children musi być niepustą tablicą")

    rendered = copy.deepcopy(template)
    rendered["manifest_absolute_path"] = str(installed_manifest)
    rendered["absolute_path"] = str(modules)
    rendered["app_dir"] = str(application)
    module_names: set[str] = set()
    module_paths: set[str] = set()
    menu_sections: set[str] = set()
    runtime_references: list[tuple[str, str]] = []
    runtime_ids = {"main"}

    for offset, child in enumerate(rendered["children"]):
        if not isinstance(child, dict) or not REQUIRED_CHILD_FIELDS.issubset(child):
            raise RenderError(f"children[{offset}] nie zawiera wymaganych pól")
        module_name = child["module_name"]
        if (
            not isinstance(module_name, str)
            or not SAFE_IDENTIFIER.fullmatch(module_name)
            or module_name in module_names
        ):
            raise RenderError(f"Nieprawidłowa lub powtórzona nazwa modułu: {module_name!r}")
        if not isinstance(child["is_menu_option"], bool) or not isinstance(child["is_runtime"], bool):
            raise RenderError(f"{module_name}: is_menu_option i is_runtime muszą być boolean")
        if child["is_runtime"] and module_name != "runtime":
            runtime_ids.add(module_name)

        template_path = child["absolute_module_path"]
        prefix = "${MODULES_DIR}/"
        if not isinstance(template_path, str) or not template_path.startswith(prefix):
            raise RenderError(f"{module_name}: absolute_module_path musi zaczynać się od {prefix}")
        relative = Path(template_path[len(prefix):])
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise RenderError(f"{module_name}: niebezpieczna ścieżka modułu")
        resolved_path = (modules / relative).resolve(strict=False)
        if not resolved_path.is_dir() or not is_below(resolved_path, modules):
            LOGGER.warning("Module directory unavailable: module=%s path=%s", module_name, resolved_path)

            raise RenderError(f"{module_name}: moduł nie istnieje w MODULES_DIR - ${resolved_path}")
        normalized = str(resolved_path)
        if normalized in module_paths:
            raise RenderError(f"Powtórzona ścieżka modułu: {normalized}")
        child["absolute_module_path"] = normalized

        runtimes = child["runtime"]
        if (
            not isinstance(runtimes, list)
            or any(not isinstance(item, str) or not SAFE_IDENTIFIER.fullmatch(item) for item in runtimes)
            or len(runtimes) != len(set(runtimes))
        ):
            raise RenderError(f"{module_name}: runtime musi być tablicą unikalnych identyfikatorów")
        runtime_references.extend((module_name, item) for item in runtimes)

        manifest_template = child["manifest_path"]
        expected_prefix = template_path + "/"
        if not isinstance(manifest_template, str) or not manifest_template.startswith(expected_prefix):
            raise RenderError(f"{module_name}: manifest_path musi być wewnątrz modułu")
        manifest_relative = Path(manifest_template[len(prefix):])
        if ".." in manifest_relative.parts:
            raise RenderError(f"{module_name}: niebezpieczna ścieżka manifestu")
        manifest_file = (modules / manifest_relative).resolve(strict=False)
        if not is_below(manifest_file, resolved_path):
            raise RenderError(f"{module_name}: manifest poza katalogiem modułu")
        child["manifest_path"] = str(manifest_file)
        try:
            detail = ManifestsApp().load_module_manifest(manifest_file, module_name)
        except (OSError, ValueError) as exc:
            raise RenderError(str(exc)) from exc
        if any(field in child for field in ("commands", "description", "usage", "menu_name")):
            raise RenderError(f"{module_name}: pomoc musi być w manifeście modułu")

        if not isinstance(detail["description"], str) or not detail["description"].strip():
            raise RenderError(f"{module_name}: description musi być niepustym tekstem")
        commands = detail["commands"]
        if not isinstance(commands, list):
            raise RenderError(f"{module_name}: commands musi być tablicą")
        command_names: set[str] = set()
        for command_offset, command in enumerate(commands):
            _validate_command(module_name, command, command_offset)
            if command["name"] in command_names:
                raise RenderError(f"{module_name}: powtórzona komenda {command['name']}")
            command_names.add(command["name"])

        if child["is_menu_option"]:
            section = child["section_name"]
            menu_name = detail["menu_name"]
            if (
                not isinstance(section, str)
                or not SECTION_NAME.fullmatch(section)
                or section in menu_sections
            ):
                raise RenderError(f"{module_name}: nieprawidłowe lub powtórzone section_name")
            if not isinstance(menu_name, str) or not menu_name.strip():
                raise RenderError(f"{module_name}: menu_name musi być niepustym tekstem")
            if not detail["usage"].strip():
                raise RenderError(f"{module_name}: usage musi być niepustym tekstem")
            menu_sections.add(section)
        elif child["section_name"] is not None or detail["menu_name"] is not None:
            raise RenderError(f"{module_name}: moduł spoza menu musi mieć null w polach menu")

        module_names.add(module_name)
        module_paths.add(normalized)

    if app_module_name not in module_names:
        raise RenderError("app_module_name nie wskazuje elementu children")
    for module_name, runtime_name in runtime_references:
        if runtime_name not in runtime_ids:
            raise RenderError(f"{module_name}: nieznany runtime {runtime_name!r}")

    unresolved = sorted({
        match.group(0)
        for value in _strings(rendered)
        for match in SHELL_REFERENCE.finditer(value)
    })
    if unresolved:
        raise RenderError("Pozostały nierozwiązane placeholdery: " + ", ".join(unresolved))

    atomic_json(output, rendered, force=force)
    verified = load_object(output)
    if any(SHELL_REFERENCE.search(value) for value in _strings(verified)):
        raise RenderError("Weryfikacja wykryła nierozwiązany placeholder")
    if verbose:
        LOGGER.info("Rendered modules manifest: path=%s", output)
    return {
        "output": str(output.resolve()),
        "manifest_path": str(installed_manifest),
        "app_dir": str(application),
        "modules_dir": str(modules),
        "modules": [item["module_name"] for item in verified["children"]],
        "count": len(verified["children"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging("render-modules-manifest")
    arguments = parser().parse_args(argv)
    package = Path(__file__).resolve().parents[2]
    try:
        output = (
            Path(arguments.output).expanduser()
            if arguments.output
            else package / "resources" / "agents-system.module.json"
        )
        result = render(
            package_dir=package,
            app_dir=Path(arguments.app_dir).expanduser(),
            modules_dir=Path(arguments.modules_dir).expanduser(),
            manifest_path=Path(arguments.manifest_path).expanduser(),
            output=output,
            force=arguments.force,
            verbose=arguments.verbose,
        )
    except RenderError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
