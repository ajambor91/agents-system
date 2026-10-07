"""List persisted agents after synchronizing runtime and OpenClaw state."""

from __future__ import annotations

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory

from collections.abc import Mapping
from typing import Any


class AgentsListService:

    """Synchronize agents.json and return the agent inventory."""

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory

    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        services = self._services_factory.create(context, flags)
        return services.registry.sync()
