"""Composition root and public API for Agents Manager."""
from __future__ import annotations

import logging

from typing import Any

from lib.configuration import Configuration
from ..open_claw import AgentToolAbstract, OpenClawFacade
from .services import (
    AgentServicesFactory,
    AgentsDeleteService,
    AgentsExecutorService,
    AgentsInstallatorService,
    AgentsListService,
    AgentsService,
    AgentsStatusService,
    AgentsToolsService,
    AgentsUpdateService,
    AgentsWakeupService,
    HelpService,
)


LOGGER = logging.getLogger(__name__)


class AgentsApplication:
    def __init__(
        self,
        configuration: Configuration,
        manifests: dict[str, Any] | None = None,
        *,
        agent_tool: AgentToolAbstract | None = None,
        services_factory: AgentServicesFactory | None = None,
    ) -> None:
        self._help_service = HelpService(manifests if manifests is not None else {})
        if services_factory is None:
            agent_tool = agent_tool if agent_tool is not None else OpenClawFacade()
            services_factory = AgentServicesFactory(configuration, agent_tool)
        installer = AgentsInstallatorService(services_factory)
        self._agents_service = AgentsService(
            services_factory,
            installer=installer,
            executor=AgentsExecutorService(services_factory),
            deleter=AgentsDeleteService(),
            updater=AgentsUpdateService(installer),
            lister=AgentsListService(services_factory),
            status=AgentsStatusService(services_factory),
            tools=AgentsToolsService(services_factory),
            wakeup=AgentsWakeupService(services_factory),
        )

    def help(
        self,
        method_name: str | None = None,
        flags: dict[str, Any] | None = None,
        module_name: str | None = None,
    ) -> dict[str, Any]:
        return self._help_service.help(method_name)

    def execute(
        self,
        method_name: str,
        flags: dict[str, Any] | None = None,
        module_name: str | None = None,
    ) -> dict[str, Any]:
        LOGGER.info('Starting application.execute method_name=%s module_name=%s agent=%s dry_run=%s', method_name, module_name, (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        return self._agents_service.exec(method_name, flags, module_name)
