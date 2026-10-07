"""Render the same menu contract for humans, agents and JSON clients."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
import sys
from typing import Any

from ..models import ApiResult
from lib.modules_catalog import ModulesCatalog, Module, Command, Flag
from lib.configuration import Configuration
from lib.unix_socket.models import Response
class Renderer:
    MODES = ("human", "human-raw", "agent", "json")
    _configuration: Configuration | None = None
    _mode: str | None = None
    _settings: type | None =None
    _color: str | None = None
    def __init__(self, configuration: Configuration, mode: str) -> None:
        self._configuration = configuration
        self._settings = type(configuration)
        self._mode = mode


    def init_mode(self):
        if self._mode is None:
            raise Exception("Mode is None")

        self._color = self._mode == "human" and sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def runtime_status(self, available) -> str:
        if available():
            return self._style("AgentsSystemCLI runtime and socket are OK", "32") + "\n\n"
        return (
            self._style("AgentsSystemCLI runtime does not working", "31")
            + "\nRunning in local mode\n\n"
        )

    def root_help(self, catalog: ModulesCatalog) -> ApiResult:
        if self._mode == "json":
            print("JSON")
            # return self._json(manifest)
        if self._mode == "agent":
            return self._json({
                "schema_version": 1,
                "kind": "asystem-agent-menu",
                "path": [],
                "usage": "asystem <section> <command> [flags]",
                "sections": [self._section_summary(name, value) for name, value in catalog.modules.values()],
            }, compact=True)
        title = self._style(self._settings.APP_NAME, "1;36")
        lines = [title, "Desc", "", "Użycie:", "  asystem [TRYB] <sekcja> <komenda> [flagi]", "", "Tryby:"]
        lines.extend([
            "  --human       czytelny, kolorowy widok (domyślny)",
            "  --human-raw   czysty tekst bez kolorów",
            "  --agent       zwarty JSON przeznaczony dla agenta",
            "  --json        pełny JSON manifestu lub wyniku",
            "  --interactive interaktywna konsola",
            "",
            "Sekcje:",
        ])
        for name, module in catalog.modules.items():
            lines.append(f"  {self._style(name, '1;33'):<20} {module.menu_name} — {module.description}")
        lines.append("\nUruchom: asystem <sekcja> --help")
        return ApiResult(stdout="\n".join(lines) + "\n", data=None)

    def section_help(self, name: str, section: Module) -> ApiResult:
        if self._mode in {"json", "agent"}:
            payload = {
                "schema_version": 1,
                "kind": "asystem-agent-section" if self._mode == "agent" else "asystem-menu-manifest",
                "path": [name],
                "section": section.section_name,
                "module_name": section.module_name,
                "menu_name": section.menu_name,
                "description": section.description,
                "usage": section.usage,
                "commands": [self._command_payload(command) for command in section.commands.values()],
            }
            return self._json(payload, compact=self._mode == "agent")
        lines = [
            self._style(section.menu_name, "1;36"),
            section.description,
            "",
            f"Użycie: {section.usage or f'asystem {name} <komenda> [flagi]'}",
            "",
            "Komendy:",
        ]
        for command in section.commands.values():
            lines.append(f"  {self._style(command.name, '1;33'):<20} {command.description}")
        lines.append(f"\nUruchom: asystem {name} <komenda> --help")
        return ApiResult(stdout="\n".join(lines) + "\n", data=section)

    def command_help(self, section_name: str, command: Command) -> ApiResult:
        if self._mode in {"json", "agent"}:
            return self._json({
                "schema_version": 1,
                "kind": "asystem-agent-command" if self._mode == "agent" else "asystem-command-help",
                "path": [section_name, command.name],
                "command": self._command_payload(command),
            }, compact=self._mode == "agent")
        lines = [
            self._style(f"{section_name} {command.name}", "1;36"),
            command.description,
            "",
            f"Użycie: {command.usage}",
        ]
        if len(command.flags) > 0:
            lines.extend(["", "Flagi:"])
            for flag in command.flags:
                tokens = [item for item in (flag.short, flag.long, *flag.aliases) if item]
                suffix = " VALUE" if flag.takes_value else ""
                required = " [wymagana]" if flag.required else ""
                lines.append(f"  {', '.join(tokens) + suffix:<32} {flag.description}{required}")
        return ApiResult(stdout="\n".join(lines) + "\n", data=command)

    def command_result(self, response: Any) -> ApiResult:
        # print(response)
        if self._mode in {"json", "agent"}:
            return self._json(response, compact=self._mode == "agent")
        if isinstance(response, dict) and "message" in response:
            message = str(response["message"])
        elif isinstance(response, str):
            message = response
        elif response is None:
            message = ""
        else:
            message = json.dumps(response, ensure_ascii=False)
        return ApiResult(stdout=message + "\n" if message else "", data=response)

    def error(self, message: str, exit_code: int = 2) -> ApiResult:
        if self._mode in {"json", "agent"}:
            payload = {"ok": False, "error": message, "exit_code": exit_code}
            result = self._json(payload, compact=self._mode == "agent")
            result.exit_code = exit_code
            return result
        return ApiResult(exit_code=exit_code, stderr=self._style(f"Błąd: {message}", "31") + "\n")

    def _style(self, value: str, code: str) -> str:
        return f"\033[{code}m{value}\033[0m" if self._color else value

    @staticmethod
    def _section_summary(name: str, section: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": name,
            "module_name": section["module_name"],
            "description": section["description"],
            "commands": [command["name"] for command in section["commands"]],
        }

    @staticmethod
    def _command_payload(command: Command) -> dict[str, Any]:
        return {
            "name": command.name,
            "method": command.method,
            "description": command.description,
            "usage": command.usage,
            "implementation_status": command.implementation_status,
            "flags": [asdict(flag) for flag in command.flags],
            "input": asdict(command.input) if command.input is not None else None,
            "exclusive_groups": [asdict(group) for group in command.exclusive_groups],
        }

    @staticmethod
    def _json(value: Any, *, compact: bool = False) -> ApiResult:
        output = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":") if compact else None,
            indent=None if compact else 2,
        ) + "\n"
        return ApiResult(stdout=output, data=value)
