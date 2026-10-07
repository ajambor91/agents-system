from __future__ import annotations

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory

from collections.abc import Mapping
from typing import Any
import json

from .state import (
    AgentStateService,
)


class AgentsExecutorService:

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory


    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:

        services = self._services_factory.create(context, flags)
        state = services.state
        runtime = services.runtime.load(flags.get('name'))
        result = services.executor.execute(
            runtime,
            flags.get("command"),
            requested_by=(
                flags.get("requested_by", context.gateway_user)
            ),
            capture=True,
            timeout_seconds=self._timeout_seconds(state, flags.get('name')),
        )

        return {
            "agent": runtime.agent_name,
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
        }

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
