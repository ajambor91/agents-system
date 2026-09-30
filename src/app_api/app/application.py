"""Manifest-driven hierarchical console application."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any, Sequence

from .models import ApiError, ApiResult
from .services.control_plane import ControlPlaneClient
from .services.manifests import ManifestCatalog, find_command
from .services.renderer import Renderer
from .services.runtime import RuntimeClient
from shared.configuration import ApplicationEnvironment


MODE_FLAGS = {
    "--human": "human",
    "--human-raw": "human-raw",
    "--agent": "agent",
    "--json": "json",
    "--interactive": "interactive",
}


class Application:
    def __init__(self, repository_root: Path | None = None) -> None:
        self.repository_root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
        self.configuration = ApplicationEnvironment.discover(self.repository_root)
        rendered_manifest = (
            self.repository_root / "resources" / "agents-system.module.json"
        )
        template_manifest = (
            self.repository_root / "resources" / "agents-system.module.template.json"
        )
        repository_manifest = (
            rendered_manifest if rendered_manifest.is_file() else template_manifest
        )
        configured_manifest = Path(
            self.configuration.select(
                "MODULES_MANIFEST_PATH",
                default=str(repository_manifest),
            )
        ).expanduser()
        manifest_path = (
            configured_manifest
            if configured_manifest.is_file()
            else rendered_manifest
            if rendered_manifest.is_file()
            else template_manifest
        )
        self.catalog = ManifestCatalog(manifest_path)
        self.control_plane = ControlPlaneClient(self.repository_root)
        self.runtime = RuntimeClient(self.configuration)

    def run(self, arguments: Sequence[str], *, use_runtime: bool = True) -> ApiResult:
        mode = "human"
        selected_modes: list[str] = []
        help_requested = False
        remaining: list[str] = []
        for token in arguments:
            if token in MODE_FLAGS:
                selected_modes.append(MODE_FLAGS[token])
            elif token in {"-h", "--help"}:
                help_requested = True
            else:
                remaining.append(token)
        if len(selected_modes) > 1:
            return Renderer("human-raw").error("Wybierz tylko jeden tryb wyjścia")
        if selected_modes:
            mode = selected_modes[0]
        try:
            if use_runtime and mode != "interactive":
                resident = self.runtime.execute(list(arguments))
                if resident is not None:
                    return resident
            manifest = self.catalog.load()
            if mode == "interactive":
                return self._interactive(manifest)
            renderer = Renderer(mode)
            if not remaining:
                return renderer.root_help(manifest)
            section_name = remaining.pop(0)
            section = manifest["sections"].get(section_name)
            if section is None:
                raise ApiError(f"Nieznana sekcja: {section_name}")
            if not remaining:
                return renderer.section_help(section_name, section)
            command_name = remaining.pop(0)
            command = find_command(section, command_name)
            if command is None:
                raise ApiError(f"Nieznana komenda w sekcji {section_name}: {command_name}")
            if help_requested:
                return renderer.command_help(section_name, command)
            arguments_map = self._parse_flags(command, remaining)
            envelope = {
                "schema_version": 1,
                "section": section_name,
                "module_name": section["module_name"],
                "command": command_name,
                "arguments": arguments_map,
                "argv": remaining,
            }
            return renderer.command_result(self.control_plane.dispatch(envelope))
        except ApiError as exc:
            return Renderer("human-raw" if mode == "interactive" else mode).error(str(exc), exc.exit_code)
        except KeyboardInterrupt:
            return Renderer("human-raw" if mode == "interactive" else mode).error(
                "przerwano przez użytkownika",
                130,
            )

    @staticmethod
    def _parse_flags(command: dict[str, Any], argv: list[str]) -> dict[str, Any]:
        by_token: dict[str, dict[str, Any]] = {}
        for flag in command.get("flags", []):
            for token in (flag.get("short"), flag["long"], *flag.get("aliases", [])):
                if token:
                    by_token[token] = flag
        values: dict[str, Any] = {}
        index = 0
        while index < len(argv):
            token = argv[index]
            inline: str | None = None
            lookup = token
            if token.startswith("--") and "=" in token:
                lookup, inline = token.split("=", 1)
            definition = by_token.get(lookup)
            if definition is None:
                raise ApiError(f"Nieznana flaga dla {command['name']}: {lookup}")
            name = definition["name"]
            if name in values:
                raise ApiError(f"Flaga {definition['long']} została podana więcej niż raz")
            if definition.get("takes_value"):
                if inline is None:
                    index += 1
                    if index >= len(argv):
                        raise ApiError(f"{definition['long']} wymaga wartości")
                    inline = argv[index]
                values[name] = inline
            else:
                if inline is not None:
                    raise ApiError(f"{definition['long']} nie przyjmuje wartości")
                values[name] = True
            index += 1
        for definition in command.get("flags", []):
            name = definition["name"]
            if name not in values and "default" in definition:
                values[name] = definition["default"]
            if definition.get("required") and name not in values:
                raise ApiError(f"{command['name']} wymaga {definition['long']}")
        return values

    def _interactive(self, manifest: dict[str, Any]) -> ApiResult:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ApiError("Tryb --interactive wymaga terminala")
        current_section: str | None = None
        renderer = Renderer("human")
        print(renderer.root_help(manifest).stdout, end="")
        while True:
            prompt = f"asystem/{current_section or ''}> "
            try:
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return ApiResult()
            if not line:
                continue
            if line in {"q", "quit", "exit"}:
                return ApiResult()
            if line in {"b", "back"}:
                current_section = None
                print(renderer.root_help(manifest).stdout, end="")
                continue
            tokens = shlex.split(line)
            if current_section is None and tokens[0] in manifest["sections"]:
                current_section = tokens.pop(0)
                if not tokens:
                    print(renderer.section_help(current_section, manifest["sections"][current_section]).stdout, end="")
                    continue
            nested = ([current_section] if current_section else []) + tokens + ["--human"]
            result = self.run(nested, use_runtime=False)
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
