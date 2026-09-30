from __future__ import annotations

import argparse
import json
import sys

from app.commands.base import (
    Command,
)
from app.services.agent_executor import (
    AgentExecutor,
)
from app.services.process import (
    ProcessRunner,
)
from app.services.runtime_config import (
    RuntimeConfigService,
)
from app.services.state import (
    AgentStateService,
)


class ExecuteCommand(Command):

    def execute(
        self,
        args: argparse.Namespace,
    ) -> int:

        runner = ProcessRunner()

        state = AgentStateService(
            self.context,
            runner,
        )

        runtime = (
            RuntimeConfigService(
                state
            )
            .load(
                args.name
            )
        )

        result = AgentExecutor(
            runner
        ).execute(
            runtime,
            args.command,
            requested_by=(
                args.requested_by
            ),
            capture=True,
            timeout_seconds=self._timeout_seconds(state, args.name),
        )

        if result.stdout:
            sys.stdout.write(
                result.stdout
            )

        if result.stderr:
            sys.stderr.write(
                result.stderr
            )

        return result.returncode

    @staticmethod
    def _timeout_seconds(
        state: AgentStateService,
        agent_name: str,
    ) -> int:
        path = state.paths(agent_name).config_json
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            timeout = document.get("execution", {}).get("timeout_seconds", 300)
        except (OSError, json.JSONDecodeError, AttributeError):
            return 300
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            return 300
        return timeout if 1 <= timeout <= 3600 else 300
