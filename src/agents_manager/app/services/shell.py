from __future__ import annotations

import json
import re
import shlex

from pathlib import Path
from typing import Any

from .state import (
    AgentStatePaths,
    AgentStateService,
)


class ShellService:

    VARIABLE_PATTERN = re.compile(
        r"\{\{([A-Z0-9_]+)\}\}"
    )

    ENVIRONMENT_PATTERN = re.compile(
        r"^[A-Z_][A-Z0-9_]*$"
    )

    def __init__(
        self,
        state: AgentStateService,
    ) -> None:

        self.state = state

    def generate(
        self,
        template_path: Path,
        paths: AgentStatePaths,
        variables: dict[str, str],
        *,
        dry_run: bool = False,
    ) -> None:

        with template_path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            template = json.load(
                handle
            )

        config = self._render_any(
            template,
            variables,
        )

        # Store resolved JSON.
        self.state.write_json(
            paths.shell_json,
            config,
            dry_run=dry_run,
        )

        self.state.write_text(
            paths.agentrc,
            self._render_agentrc(
                config
            ),
            dry_run=dry_run,
        )

        self.state.write_text(
            paths.bashrc,
            self._render_bashrc(
                config
            ),
            dry_run=dry_run,
        )

    def _render_any(
        self,
        value: Any,
        variables: dict[str, str],
    ) -> Any:

        if isinstance(
            value,
            str,
        ):

            return (
                self.VARIABLE_PATTERN.sub(
                    lambda match:
                    self._lookup(
                        match.group(1),
                        variables,
                    ),
                    value,
                )
            )

        if isinstance(
            value,
            list,
        ):

            return [
                self._render_any(
                    item,
                    variables,
                )
                for item
                in value
            ]

        if isinstance(
            value,
            dict,
        ):

            return {
                key: self._render_any(
                    item,
                    variables,
                )
                for key, item
                in value.items()
            }

        return value

    @staticmethod
    def _lookup(
        key: str,
        variables: dict[str, str],
    ) -> str:

        if key not in variables:
            raise ValueError(
                f"Unknown template "
                f"variable: {key}"
            )

        return variables[key]

    def _render_exports(
        self,
        items: list[dict],
    ) -> list[str]:

        lines: list[str] = []

        for item in items:

            name = item["name"]

            if not (
                self.ENVIRONMENT_PATTERN
                .fullmatch(name)
            ):
                raise ValueError(
                    "Invalid environment "
                    f"variable: {name}"
                )

            value = str(
                item["value"]
            )

            lines.append(
                f"export {name}="
                f"{shlex.quote(value)}"
            )

        return lines

    def _render_agentrc(
        self,
        config: dict,
    ) -> str:

        lines = [
            "#!/usr/bin/env bash",
            "",
            "# AUTO-GENERATED.",
            "# DO NOT EDIT.",
            "",
        ]

        lines += self._render_exports(
            config.get(
                "environment",
                [],
            )
        )

        path_entries = config.get(
            "path",
            [],
        )

        if path_entries:

            prefix = ":".join(
                str(item)
                for item
                in path_entries
            )

            lines += [
                "",
                (
                    f"export PATH="
                    f"{shlex.quote(prefix)}:"
                    f"\"$PATH\""
                ),
            ]

        commands = config.get(
            "agentrc_commands",
            [],
        )

        if commands:
            lines.append("")

            lines += [
                str(item["command"])
                for item
                in commands
            ]

        lines.append("")

        return "\n".join(
            lines
        )

    def _render_bashrc(
        self,
        config: dict,
    ) -> str:

        bash = config.get(
            "bashrc",
            {},
        )

        lines = [
            "#!/usr/bin/env bash",
            "",
            "# AUTO-GENERATED.",
            "# DO NOT EDIT.",
            "",
            (
                '[[ -f "$HOME/.agentrc" ]] '
                '&& source "$HOME/.agentrc"'
            ),
            "",
        ]

        lines += self._render_exports(
            bash.get(
                "environment",
                [],
            )
        )

        for item in bash.get(
            "shell_options",
            [],
        ):
            lines.append(
                str(item["command"])
            )

        for source in bash.get(
            "sources",
            [],
        ):

            path = shlex.quote(
                str(source["path"])
            )

            if source.get(
                "optional",
                False,
            ):

                lines.append(
                    f"[[ -f {path} ]] "
                    f"&& source {path}"
                )

            else:
                lines.append(
                    f"source {path}"
                )

        for item in bash.get(
            "commands",
            [],
        ):
            lines.append(
                str(item["command"])
            )

        prompt = bash.get(
            "prompt",
            {},
        )

        if prompt.get(
            "enabled"
        ):

            lines.append(
                "PS1="
                + shlex.quote(
                    str(
                        prompt["value"]
                    )
                )
            )

        lines.append("")

        return "\n".join(
            lines
        )