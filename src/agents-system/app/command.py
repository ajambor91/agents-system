"""JSON-driven command parsing and help rendering."""

from __future__ import annotations

import json
import os
import re
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, InputError
from .models import CommandRequest


FLAG_NAME = re.compile(r"^--[a-z][a-z0-9-]*$")
SHORT_NAME = re.compile(r"^-[A-Za-z0-9]$")


class Command:
    """Parse one argv list strictly according to a validated JSON contract."""

    def __init__(
        self,
        spec: dict[str, Any],
        *,
        environment: Mapping[str, str] | None = None,
        variable_resolver: Callable[[str], str | None] | None = None,
        environment_first: bool = False,
    ) -> None:
        self.spec = spec
        self.environment = os.environ if environment is None else environment
        self.variable_resolver = variable_resolver
        self.environment_first = environment_first

    @staticmethod
    def load_specs(directory: Path, targets: set[str]) -> dict[str, dict[str, Any]]:
        """Load and validate every command contract before any dispatch."""
        specs: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ConfigurationError(f"Nieprawidłowa definicja komendy {path}: {exc}") from exc
            if not isinstance(value, dict) or value.get("schema_version") != 1:
                raise ConfigurationError(f"{path}: wymagany schema_version równy 1")
            name = value.get("command")
            if not isinstance(name, str) or not name or name in specs:
                raise ConfigurationError(f"{path}: brak albo powtórzona nazwa command")
            target = value.get("target", {}).get("command_class")
            if target not in targets:
                raise ConfigurationError(f"{path}: nieznany target.command_class {target!r}")
            seen: set[str] = set()
            for flag in value.get("flags", []):
                long = flag.get("long")
                short = flag.get("short")
                if not isinstance(long, str) or not FLAG_NAME.fullmatch(long):
                    raise ConfigurationError(f"{path}: nieprawidłowa długa flaga {long!r}")
                if short is not None and (not isinstance(short, str) or not SHORT_NAME.fullmatch(short)):
                    raise ConfigurationError(f"{path}: nieprawidłowa krótka flaga {short!r}")
                if long in seen or (short is not None and short in seen):
                    raise ConfigurationError(f"{path}: powtórzona flaga {long}")
                seen.add(long)
                if short:
                    seen.add(short)
            specs[name] = value
        if not specs:
            raise ConfigurationError(f"Brak definicji komend w {directory}")
        return specs

    def parse(self, argv: Sequence[str]) -> CommandRequest | None:
        """Return a typed request, or None after rendering is requested by --help."""
        flags = self.spec.get("flags", [])
        by_token: dict[str, dict[str, Any]] = {}
        for item in flags:
            by_token[item["long"]] = item
            if item.get("short"):
                by_token[item["short"]] = item
        explicit: dict[str, Any] = {}
        sources: dict[str, str] = {}
        positional_tokens: list[str] = []
        index = 0
        while index < len(argv):
            token = argv[index]
            inline: str | None = None
            lookup = token
            if token.startswith("--") and "=" in token:
                lookup, inline = token.split("=", 1)
            if lookup.startswith("-"):
                definition = by_token.get(lookup)
                if definition is None:
                    raise InputError(f"Nieznana flaga dla {self.spec['command']}: {lookup}")
                destination = definition.get("destination", definition["long"][2:].replace("-", "_"))
                if destination in explicit:
                    raise InputError(f"Flaga {definition['long']} została podana więcej niż raz")
                takes_value = bool(definition.get("takes_value"))
                if takes_value:
                    if inline is None:
                        index += 1
                        if index >= len(argv) or argv[index].startswith("-"):
                            raise InputError(f"{definition['long']} wymaga wartości")
                        inline = argv[index]
                    explicit[destination] = self._convert(inline, definition)
                else:
                    if inline is not None:
                        explicit[destination] = self._boolean(inline, definition["long"])
                    else:
                        explicit[destination] = True
                sources[destination] = "cli"
            else:
                positional_tokens.append(token)
            index += 1

        if explicit.get("help"):
            return None

        values: dict[str, Any] = {}
        for definition in flags:
            destination = definition.get("destination", definition["long"][2:].replace("-", "_"))
            env_name = definition.get("env")
            if self.environment_first and env_name and env_name in self.environment:
                values[destination] = self._convert(self.environment[env_name], definition)
                sources[destination] = "environment"
                continue
            if destination in explicit:
                values[destination] = explicit[destination]
                continue
            value: Any = None
            source = "missing"
            if definition.get("var") and self.variable_resolver is not None:
                resolved = self.variable_resolver(str(definition["var"]))
                if resolved is not None:
                    value = self._convert(resolved, definition)
                    source = "app_env"
            if source == "missing" and "default" in definition:
                value = definition["default"]
                source = "default"
            if definition.get("required") and (value is None or value == ""):
                raise InputError(f"{self.spec['command']} wymaga {definition['long']}")
            values[destination] = value
            sources[destination] = source

        positional = self.spec.get("positionals", [])
        if len(positional_tokens) > len(positional):
            raise InputError(f"Nieoczekiwany argument: {positional_tokens[len(positional)]}")
        for offset, definition in enumerate(positional):
            value = positional_tokens[offset] if offset < len(positional_tokens) else definition.get("default")
            if definition.get("required") and (value is None or value == ""):
                raise InputError(f"Brak argumentu {definition['name']}")
            values[definition["name"]] = value
            sources[definition["name"]] = "cli" if offset < len(positional_tokens) else "default"

        for group in self.spec.get("exclusive_groups", []):
            selected = [name for name in group["members"] if values.get(name)]
            minimum = int(group.get("minimum", 0))
            maximum = int(group.get("maximum", 1))
            if not minimum <= len(selected) <= maximum:
                rendered = ", ".join("--" + name.replace("_", "-") for name in group["members"])
                raise InputError(f"Wybierz {minimum if minimum == maximum else 'odpowiednią liczbę'} z: {rendered}")

        if values.get("help"):
            return None
        return CommandRequest(
            command=self.spec["command"],
            arguments=values,
            sources=sources,
            actor={"uid": os.getuid(), "effective_uid": os.geteuid(), "user": self.environment.get("USER")},
            request_id=str(uuid.uuid4()),
        )

    def help(self) -> str:
        """Render command help entirely from its JSON definition."""
        lines = [f"Użycie: {self.spec.get('usage', self.spec['command'])}", self.spec.get("description", ""), "", "Flagi:"]
        for flag in self.spec.get("flags", []):
            names = ", ".join(value for value in (flag.get("short"), flag["long"]) if value)
            if flag.get("takes_value"):
                names += " VALUE"
            required = " [wymagana]" if flag.get("required") else ""
            lines.append(f"  {names:<28} {flag.get('description', '')}{required}")
        for item in self.spec.get("positionals", []):
            lines.append(f"  {item['name']:<28} {item.get('description', '')}")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _boolean(value: str, name: str) -> bool:
        normalized = value.lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise InputError(f"{name} przyjmuje true albo false")

    def _convert(self, value: str, definition: dict[str, Any]) -> Any:
        kind = definition.get("type", "string")
        if kind == "boolean":
            return self._boolean(value, definition["long"])
        if kind == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise InputError(f"{definition['long']} wymaga poprawnego JSON: {exc}") from exc
        return value
