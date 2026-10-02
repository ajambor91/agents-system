"""Render the same menu contract for humans, agents and JSON clients."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from ..models import ApiResult


class Renderer:
    MODES = ("human", "human-raw", "agent", "json")

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.color = mode == "human" and sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def runtime_status(self, available: bool) -> str:
        if available:
            return self._style("Application runtime and socket are OK", "32") + "\n\n"
        return (
            self._style("Application runtime does not working", "31")
            + "\nRunning in local mode\n\n"
        )

    def root_help(self, manifest: dict[str, Any]) -> ApiResult:
        if self.mode == "json":
            return self._json(manifest)
        if self.mode == "agent":
            return self._json({
                "schema_version": 1,
                "kind": "asystem-agent-menu",
                "path": [],
                "usage": "asystem <section> <command> [flags]",
                "sections": [self._section_summary(name, value) for name, value in manifest["sections"].items()],
            }, compact=True)
        title = self._style(manifest["menu_name"], "1;36")
        lines = [title, manifest["description"], "", "Użycie:", "  asystem [TRYB] <sekcja> <komenda> [flagi]", "", "Tryby:"]
        lines.extend([
            "  --human       czytelny, kolorowy widok (domyślny)",
            "  --human-raw   czysty tekst bez kolorów",
            "  --agent       zwarty JSON przeznaczony dla agenta",
            "  --json        pełny JSON manifestu lub wyniku",
            "  --interactive interaktywna konsola",
            "",
            "Sekcje:",
        ])
        for name, section in manifest["sections"].items():
            lines.append(f"  {self._style(name, '1;33'):<20} {section['menu_name']} — {section['description']}")
        lines.append("\nUruchom: asystem <sekcja> --help")
        return ApiResult(stdout="\n".join(lines) + "\n", data=manifest)

    def section_help(self, name: str, section: dict[str, Any]) -> ApiResult:
        if self.mode in {"json", "agent"}:
            payload = {
                "schema_version": 1,
                "kind": "asystem-agent-section" if self.mode == "agent" else section["kind"],
                "path": [name],
                "section": section,
            }
            return self._json(payload, compact=self.mode == "agent")
        lines = [
            self._style(section["menu_name"], "1;36"),
            section["description"],
            "",
            f"Użycie: asystem {name} <komenda> [flagi]",
            "",
            "Komendy:",
        ]
        for command in section["commands"]:
            lines.append(f"  {self._style(command['name'], '1;33'):<20} {command['description']}")
        lines.append(f"\nUruchom: asystem {name} <komenda> --help")
        return ApiResult(stdout="\n".join(lines) + "\n", data=section)

    def command_help(self, section_name: str, command: dict[str, Any]) -> ApiResult:
        if self.mode in {"json", "agent"}:
            return self._json({
                "schema_version": 1,
                "kind": "asystem-agent-command" if self.mode == "agent" else "asystem-command-help",
                "path": [section_name, command["name"]],
                "command": command,
            }, compact=self.mode == "agent")
        lines = [
            self._style(f"{section_name} {command['name']}", "1;36"),
            command["description"],
            "",
            f"Użycie: {command['usage']}",
        ]
        if command.get("flags"):
            lines.extend(["", "Flagi:"])
            for flag in command["flags"]:
                tokens = [item for item in (flag.get("short"), flag["long"], *flag.get("aliases", [])) if item]
                suffix = " VALUE" if flag.get("takes_value") else ""
                required = " [wymagana]" if flag.get("required") else ""
                lines.append(f"  {', '.join(tokens) + suffix:<32} {flag['description']}{required}")
        return ApiResult(stdout="\n".join(lines) + "\n", data=command)

    def command_result(self, response: Any) -> ApiResult:
        if self.mode in {"json", "agent"}:
            return self._json(response, compact=self.mode == "agent")
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
        if self.mode in {"json", "agent"}:
            payload = {"ok": False, "error": message, "exit_code": exit_code}
            result = self._json(payload, compact=self.mode == "agent")
            result.exit_code = exit_code
            return result
        return ApiResult(exit_code=exit_code, stderr=self._style(f"Błąd: {message}", "31") + "\n")

    def _style(self, value: str, code: str) -> str:
        return f"\033[{code}m{value}\033[0m" if self.color else value

    @staticmethod
    def _section_summary(name: str, section: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": name,
            "module_name": section["module_name"],
            "description": section["description"],
            "commands": [command["name"] for command in section["commands"]],
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
