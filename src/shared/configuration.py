"""Read application configuration without implicitly exporting it to the process."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


REFERENCE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
UNSET = object()


class ConfigurationValueError(RuntimeError):
    """The installed app_env.json cannot be used safely."""


class ApplicationEnvironment:
    """Resolve config, CLI and shell values according to the installation mode.

    The document always decides INSTALL_MODE and BASH_SOURCE.  Shell variables
    cannot enable shell precedence by themselves.  No value is copied into
    ``os.environ`` by this class.
    """

    def __init__(
        self,
        document: Mapping[str, Any],
        *,
        source: Path,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.source = source.resolve(strict=False)
        self.environment = os.environ if environment is None else environment
        self.values = self._resolve(self._read_variables(document))
        self.mode = self.require("INSTALL_MODE")
        if self.mode not in {"dev", "system"}:
            raise ConfigurationValueError(
                f"{self.source}: INSTALL_MODE musi mieć wartość dev albo system"
            )
        self.shell_source_enabled = (
            self.mode == "dev" and self._as_bool(self.values.get("BASH_SOURCE", "false"))
        )

    @classmethod
    def discover(
        cls,
        repository_root: Path,
        *,
        environment: Mapping[str, str] | None = None,
        path: Path | None = None,
    ) -> "ApplicationEnvironment":
        root = repository_root.expanduser().resolve()
        candidates = [path] if path is not None else [
            root / "resources" / "app_env.json",
            root / "src" / "resources" / "app_env.json",
        ]
        selected = next((candidate for candidate in candidates if candidate and candidate.is_file()), None)
        if selected is None:
            rendered = ", ".join(str(candidate) for candidate in candidates if candidate)
            raise ConfigurationValueError(f"Brak app_env.json; sprawdzono: {rendered}")
        try:
            document = json.loads(selected.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationValueError(f"Nie można odczytać {selected}: {exc}") from exc
        bootstrap = cls(document, source=selected, environment=environment)
        if bootstrap.mode != "system":
            return bootstrap
        central = Path(bootstrap.require("APP_ENV_PATH"))
        if not central.is_file() or central.resolve(strict=False) == selected.resolve(strict=False):
            return bootstrap
        try:
            central_document = json.loads(central.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationValueError(f"Nie można odczytać {central}: {exc}") from exc
        return cls(central_document, source=central, environment=environment)

    def select(
        self,
        name: str,
        *,
        flag: Any = UNSET,
        default: Any = UNSET,
    ) -> Any:
        """Return shell > CLI > JSON in enabled dev mode, else CLI > JSON."""
        if self.shell_source_enabled and name in self.environment:
            return self.environment[name]
        if flag is not UNSET and flag is not None:
            return flag
        if name in self.values:
            return self.values[name]
        if default is not UNSET:
            return default
        raise ConfigurationValueError(f"{self.source}: brak zmiennej {name}")

    def require(self, name: str) -> str:
        value = self.values.get(name)
        if value is None or value == "":
            raise ConfigurationValueError(f"{self.source}: brak zmiennej {name}")
        return value

    @staticmethod
    def _read_variables(document: Mapping[str, Any]) -> dict[str, str]:
        if document.get("schema_version") != 1 or document.get("kind") != "agents-system-environment":
            raise ConfigurationValueError("app_env.json ma nieprawidłowy kontrakt")
        variables = document.get("variables")
        if not isinstance(variables, list):
            raise ConfigurationValueError("app_env.json nie zawiera tablicy variables")
        values: dict[str, str] = {}
        for offset, item in enumerate(variables):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ConfigurationValueError(f"variables[{offset}] ma nieprawidłowy format")
            name = item["name"]
            if name in values:
                raise ConfigurationValueError(f"Powtórzona zmienna: {name}")
            raw = item.get("value")
            if isinstance(raw, bool):
                values[name] = "true" if raw else "false"
            elif isinstance(raw, (str, int, float)):
                values[name] = str(raw)
            else:
                raise ConfigurationValueError(f"{name}.value musi być wartością skalarną")
        return values

    @staticmethod
    def _resolve(raw: Mapping[str, str]) -> dict[str, str]:
        resolved: dict[str, str] = {}

        def visit(name: str, stack: tuple[str, ...]) -> str:
            if name in resolved:
                return resolved[name]
            if name not in raw:
                raise ConfigurationValueError(f"Nieznany placeholder ${{{name}}}")
            if name in stack:
                raise ConfigurationValueError("Cykl placeholderów: " + " -> ".join((*stack, name)))
            value = REFERENCE.sub(lambda match: visit(match.group(1), (*stack, name)), raw[name])
            resolved[name] = value
            return value

        for name in raw:
            visit(name, ())
        return resolved

    @staticmethod
    def _as_bool(value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
        raise ConfigurationValueError("BASH_SOURCE musi mieć wartość boolean")
