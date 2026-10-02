"""Separate console options from manifest-defined application arguments."""
from collections.abc import Sequence
from typing import Any

from ..exceptions import ApiError
from ..models.console_arguments import ConsoleArguments
from .manifests import find_command


MODE_FLAGS = {
    "--human": "human",
    "--human-raw": "human-raw",
    "--agent": "agent",
    "--json": "json",
    "--interactive": "interactive",
}


class ConsoleArgumentParser:
    @staticmethod
    def parse(manifest: dict[str, Any], arguments: Sequence[str]) -> ConsoleArguments:
        result = ConsoleArguments()
        selected_modes: list[str] = []
        module_flags: dict[str, dict[str, Any]] = {}
        awaiting_value = False
        positional_only = False
        for token in arguments:
            if awaiting_value or positional_only:
                result.remaining.append(token)
                awaiting_value = False
                continue
            if len(result.remaining) >= 2 and token == "--":
                result.remaining.append(token)
                positional_only = True
                continue
            lookup = token.split("=", 1)[0] if token.startswith("--") else token
            definition = module_flags.get(lookup)
            if definition is not None:
                # After selection, a declared module flag belongs to the module,
                # including flags sharing names with console options.
                result.remaining.append(token)
                awaiting_value = bool(definition.get("takes_value")) and "=" not in token
                continue
            if token in MODE_FLAGS:
                selected_modes.append(MODE_FLAGS[token])
            elif token in {"-h", "--help"}:
                result.help_requested = True
            else:
                result.remaining.append(token)
                if len(result.remaining) == 2:
                    section = manifest["sections"].get(result.remaining[0])
                    command = find_command(section, token) if section is not None else None
                    if command is not None:
                        for flag in command.get("flags", []):
                            for alias in (flag.get("short"), flag["long"], *flag.get("aliases", [])):
                                if alias:
                                    module_flags[alias] = flag
        if len(selected_modes) > 1:
            raise ApiError("Wybierz tylko jeden tryb wyjścia")
        if selected_modes:
            result.mode = selected_modes[0]
        return result
