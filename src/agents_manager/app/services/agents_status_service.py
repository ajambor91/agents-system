"""Show one synchronized agent record and its recent tasks."""

from __future__ import annotations

import logging

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory

from collections.abc import Mapping
from typing import Any

from .agent_catalog import AgentCatalog
from .agent_registry import AgentRegistryService


LOGGER = logging.getLogger(__name__)


class AgentsStatusService:

    """Synchronize agents.json and return one selected agent."""

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory

    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        LOGGER.info('Reading agent status agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        if not AgentCatalog.AGENT_PATTERN.fullmatch(flags.get('name')):
            raise ValueError(f"Invalid agent name: {flags.get('name')}")

        services = self._services_factory.create(context, flags)
        document = services.registry.sync()
        return AgentRegistryService.get(
            document,
            flags.get('name'),
        )
