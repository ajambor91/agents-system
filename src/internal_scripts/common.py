"""Shared validation and atomic JSON operations for internal renderers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from lib.json_loader import JsonLoader
from manifests import ManifestsApp


SHELL_REFERENCE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
DOUBLE_REFERENCE = re.compile(r"\{\{([^{}]+)\}\}")
SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]*$")
SAFE_VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class RenderError(RuntimeError):
    """Expected contract or input failure rendered without a traceback."""


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = ManifestsApp().load_manifest(path)
        if not isinstance(value, dict):
            raise ValueError(f"Dokument musi być obiektem JSON: {path}")
        return value
    except (OSError, ValueError) as exc:
        raise RenderError(f"Nie można odczytać JSON {path}: {exc}") from exc


def load_name_values(path: Path) -> dict[str, str | None]:
    try:
        value = JsonLoader.load(path)
    except FileNotFoundError as exc:
        raise RenderError(f"Brak pliku wartości domyślnych: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"Nie można odczytać wartości domyślnych {path}: {exc}") from exc
    if not isinstance(value, list):
        raise RenderError(f"{path}: oczekiwano tablicy name/value")
    result: dict[str, str | None] = {}
    for offset, item in enumerate(value):
        if not isinstance(item, dict):
            raise RenderError(f"{path}: element {offset} musi być obiektem")
        name = item.get("name")
        item_value = item.get("value")
        if not isinstance(name, str) or not SAFE_VARIABLE.fullmatch(name) or name in result:
            raise RenderError(f"{path}: nieprawidłowa lub powtórzona nazwa {name!r}")
        if item_value is not None and (not isinstance(item_value, str) or not item_value):
            raise RenderError(f"{path}: {name}.value musi być tekstem albo null")
        result[name] = item_value
    return result


def require_absolute_directory(value: str, name: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise RenderError(f"{name} musi być bezpieczną ścieżką absolutną")
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise RenderError(f"{name} nie jest istniejącym katalogiem: {resolved}")
    return resolved


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_values(raw: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}

    def visit(name: str, stack: tuple[str, ...]) -> str:
        if name in resolved:
            return resolved[name]
        if name not in raw:
            raise RenderError(f"Nieznany placeholder ${{{name}}}")
        if name in stack:
            raise RenderError("Cykliczne placeholdery: " + " -> ".join((*stack, name)))
        value = raw[name]
        rendered = SHELL_REFERENCE.sub(lambda match: visit(match.group(1), (*stack, name)), value)
        resolved[name] = rendered
        return rendered

    for variable in raw:
        visit(variable, ())
    return resolved


def atomic_json(path: Path, value: Any, *, force: bool, mode: int = 0o640) -> None:
    if path.is_symlink():
        raise RenderError(f"Cel nie może być dowiązaniem symbolicznym: {path}")
    if path.exists() and not force:
        raise RenderError(f"Plik już istnieje; użyj --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
        temporary_name = None
    except OSError as exc:
        raise RenderError(f"Nie można zapisać {path}: {exc}") from exc
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
