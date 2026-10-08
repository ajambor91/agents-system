"""Show the tool policy currently authored for one OpenClaw agent."""

from __future__ import annotations

import logging

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory

from collections.abc import Mapping
from typing import Any

from .agent_catalog import AgentCatalog


LOGGER = logging.getLogger(__name__)


class AgentsToolsService:

    """Read the applied OpenClaw tool policy without mutating it."""

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory

    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        LOGGER.info('Reading agent tools agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        if not AgentCatalog.AGENT_PATTERN.fullmatch(flags.get('name')):
            raise ValueError(f"Invalid agent name: {flags.get('name')}")
        services = self._services_factory.create(context, flags)
        policy = services.agent_tool.get_agent_tools(flags.get('name'))
        return {"agent": flags.get('name'), "tools": policy}
