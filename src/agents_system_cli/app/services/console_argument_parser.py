"""Separate console options from manifest-defined application arguments."""
from collections.abc import Sequence
from typing import Any

from ..exceptions import ApiError
from ..models import ConsoleArguments
from  lib.modules_catalog import ModulesCatalog, Module, Command, Flag

MODE_FLAGS = {
    "--human": "human",
    "--human-raw": "human-raw",
    "--agent": "agent",
    "--json": "json",
    "--interactive": "interactive",
}


class ConsoleArgumentParser:
    @staticmethod
    def parse(manifest: ModulesCatalog, arguments: Sequence[str]) -> ConsoleArguments:
        result = ConsoleArguments()
        selected_modes: list[str] = []
        module_flags: dict[str, Flag] = {}
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
                awaiting_value = bool(definition.takes_value) and "=" not in token
                continue
            if token in MODE_FLAGS:
                selected_modes.append(MODE_FLAGS[token])
            elif token in {"-h", "--help"}:
                result.help_requested = True
            else:
                result.remaining.append(token)
                if len(result.remaining) == 2:
                    section = None
                    if result.remaining[0] in manifest.modules:
                        section = manifest.modules[result.remaining[0]]
                    elif result.remaining[0] in manifest.modules_by_section:
                        section = manifest.modules_by_section[result.remaining[0]]

                    command = section.commands.get(token) if section is not None else None
                    if command is not None:
                        for flag in command.flags:
                            if flag.name == "help":
                                continue
                            for alias in (flag.short, flag.long, *flag.aliases):
                                if alias:
                                    module_flags[alias] = flag
        if len(selected_modes) > 1:
            raise ApiError("Wybierz tylko jeden tryb wyjścia")
        if selected_modes:
            result.mode = selected_modes[0]
        return result
