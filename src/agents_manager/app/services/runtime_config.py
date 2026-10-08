from __future__ import annotations

import logging

import json

from pathlib import Path

from .agent_executor import (
    AgentRuntime,
)
from .state import (
    AgentStatePaths,
    AgentStateService,
)


LOGGER = logging.getLogger(__name__)


class RuntimeConfigService:

    def __init__(
        self,
        state: AgentStateService,
    ) -> None:

        self.state = state

    def write(
        self,
        paths: AgentStatePaths,
        runtime: AgentRuntime,
        *,
        gateway_user: str,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Writing agent runtime configuration dry_run=%s', dry_run)
        data = {
            "version": 1,

            "agent": (
                runtime.agent_name
            ),

            "linux_user": (
                runtime.linux_user
            ),

            "gateway_user": (
                gateway_user
            ),

            "home": str(
                runtime.home
            ),

            "workspace": str(
                runtime.workspace
            ),

            "shell": str(
                runtime.shell
            ),

            "agentrc": str(
                runtime.agentrc
            ),
        }

        self.state.write_json(
            paths.runtime_json,
            data,
            dry_run=dry_run,
        )

    def load(
        self,
        agent_name: str,
    ) -> AgentRuntime:

        LOGGER.debug('Loading agent runtime configuration agent_name=%s', agent_name)
        path = (
            self.state
            .paths(agent_name)
            .runtime_json
        )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            data = json.load(
                handle
            )

        if (
            data.get("agent")
            != agent_name
        ):
            raise RuntimeError(
                "Runtime config agent "
                f"mismatch in {path}"
            )

        return AgentRuntime(
            agent_name=data["agent"],

            linux_user=(
                data["linux_user"]
            ),

            home=Path(
                data["home"]
            ),

            workspace=Path(
                data["workspace"]
            ),

            shell=Path(
                data["shell"]
            ),

            agentrc=Path(
                data["agentrc"]
            ),
        )