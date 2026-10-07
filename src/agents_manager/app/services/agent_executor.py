from __future__ import annotations

import json
import subprocess
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .process import (
    ProcessRunner,
)


@dataclass(frozen=True)
class AgentRuntime:
    agent_name: str
    linux_user: str

    home: Path
    workspace: Path

    shell: Path
    agentrc: Path


class AgentExecutor:

    HISTORY_DIRECTORY = ".history"
    HISTORY_FILE = "history.json"
    SEARCH_HISTORY_DIRECTORY = "searches"

    def __init__(
        self,
        process_runner: ProcessRunner,
    ) -> None:

        self.process_runner = (
            process_runner
        )

    def execute(
        self,
        runtime: AgentRuntime,
        command: str,
        *,
        requested_by: str | None = None,
        capture: bool = True,
        timeout_seconds: int | None = None,
    ) -> subprocess.CompletedProcess[str]:

        if not command.strip():
            raise ValueError(
                "Command cannot be empty."
            )

        requested_by = (
            requested_by
            or runtime.linux_user
        )

        self.prepare_history(
            runtime
        )

        execution_id = uuid.uuid4().hex

        self._append_history(
            runtime,
            {
                "timestamp": self._timestamp(),
                "event": "command_started",
                "execution_id": execution_id,
                "agent": runtime.agent_name,
                "requested_by": requested_by,
                "command": command,
                "working_directory": str(
                    runtime.workspace
                ),
            },
        )

        bootstrap = (
            'set -eo pipefail\n'
            'source "$1"\n'
            'cd "$2"\n'
            'export AGENT_REQUESTED_BY="$4"\n'
            'eval -- "$3"\n'
        )

        result = (
            self.process_runner
            .run_as_user(
                runtime.linux_user,
                [
                    str(runtime.shell),

                    "--noprofile",
                    "--norc",

                    "-c",
                    bootstrap,

                    "agent-executor",

                    str(
                        runtime.agentrc
                    ),

                    str(
                        runtime.workspace
                    ),

                    command,

                    requested_by,
                ],
                check=False,
                capture=capture,
                timeout=timeout_seconds,
            )
        )

        self._append_history(
            runtime,
            {
                "timestamp": self._timestamp(),
                "event": "command_completed",
                "execution_id": execution_id,
                "agent": runtime.agent_name,
                "requested_by": requested_by,
                "command": command,
                "return_code": result.returncode,
            },
        )

        return result

    def prepare_history(
        self,
        runtime: AgentRuntime,
        *,
        dry_run: bool = False,
    ) -> None:

        history_directory = (
            runtime.home
            / self.HISTORY_DIRECTORY
        )

        search_directory = (
            history_directory
            / self.SEARCH_HISTORY_DIRECTORY
        )

        history_file = (
            history_directory
            / self.HISTORY_FILE
        )

        if dry_run:
            self.process_runner.report(
                f"[DRY] create agent history "
                f"{history_directory}"
            )
            self.process_runner.report(
                f"[DRY] initialize "
                f"{history_file}"
            )
            return

        initial_entry = json.dumps(
            {
                "timestamp": self._timestamp(),
                "event": "agent_directory_created",
                "agent": runtime.agent_name,
                "message": "Agent's dir created",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

        bootstrap = (
            'set -euo pipefail\n'
            'install -d -m 0700 -- "$1" "$2"\n'
            'if [[ ! -e "$3" ]]; then\n'
            '    printf "%s\\n" "$4" > "$3"\n'
            '    chmod 0600 "$3"\n'
            'fi\n'
        )

        self.process_runner.run_as_user(
            runtime.linux_user,
            [
                str(runtime.shell),
                "--noprofile",
                "--norc",
                "-c",
                bootstrap,
                "agent-history-init",
                str(history_directory),
                str(search_directory),
                str(history_file),
                initial_entry,
            ],
        )

    def _append_history(
        self,
        runtime: AgentRuntime,
        entry: dict[str, object],
    ) -> None:

        history_file = (
            runtime.home
            / self.HISTORY_DIRECTORY
            / self.HISTORY_FILE
        )

        serialized = json.dumps(
            entry,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        bootstrap = (
            'set -euo pipefail\n'
            'printf "%s\\n" "$1" >> "$2"\n'
            'chmod 0600 "$2"\n'
        )

        self.process_runner.run_as_user(
            runtime.linux_user,
            [
                str(runtime.shell),
                "--noprofile",
                "--norc",
                "-c",
                bootstrap,
                "agent-history-append",
                serialized,
                str(history_file),
            ],
        )

    @staticmethod
    def _timestamp() -> str:

        return (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
