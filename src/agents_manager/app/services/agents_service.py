"""Dispatch typed application operations to their dedicated services."""
from __future__ import annotations

import logging

from collections.abc import Mapping
from typing import Any

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory
from .agents_installator_service import AgentsInstallatorService
from .agents_executor_service import AgentsExecutorService
from .agents_delete_service import AgentsDeleteService
from .agents_update_service import AgentsUpdateService
from .agents_list_service import AgentsListService
from .agents_status_service import AgentsStatusService
from .agents_tools_service import AgentsToolsService
from .agents_wakeup_service import AgentsWakeupService


LOGGER = logging.getLogger(__name__)


class AgentsService:
    def __init__(self, services_factory: AgentServicesFactory, *,
                 installer: AgentsInstallatorService, executor: AgentsExecutorService,
                 deleter: AgentsDeleteService, updater: AgentsUpdateService,
                 lister: AgentsListService, status: AgentsStatusService,
                 tools: AgentsToolsService, wakeup: AgentsWakeupService) -> None:
        self._services_factory = services_factory

        self._installer = installer
        self._executor = executor
        self._deleter = deleter
        self._updater = updater
        self._lister = lister
        self._status = status
        self._tools = tools
        self._wakeup = wakeup

    def exec(self, method_name: str, flags: Mapping[str, Any] | None = None, module_name: str | None = None) -> dict[str, Any]:
        LOGGER.debug('Starting agents_service.exec method_name=%s module_name=%s agent=%s dry_run=%s', method_name, module_name, (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            # The exec operation uses execute to avoid calling this dispatcher recursively.
            action_name = 'execute' if method_name == 'exec' else method_name
            action = getattr(self, action_name, None)
            if action is None or action_name.startswith('_') or not callable(action):
                return {'message': 'Method not found'}
            result = action(flags)
            if not isinstance(result, dict):
                raise TypeError('Method must return a dictionary')
            LOGGER.info("Agent operation completed: method=%s status=%s", method_name, result.get('status', 'returned'))
            return result
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=exec")
            return {'message': str(exc)}

    def _create_context(self, flags: Mapping[str, Any]) -> ApplicationContext:
        return self._services_factory.create_context(flags)

    def install(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.info('Starting agents_service.install agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._installer.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=install")
            return {'message': str(exc)}

    def execute(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.info('Starting agents_service.execute agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._executor.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=execute")
            return {'message': str(exc)}

    def delete(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.info('Starting agents_service.delete agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._deleter.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=delete")
            return {'message': str(exc)}

    def update(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.info('Starting agents_service.update agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._updater.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=update")
            return {'message': str(exc)}

    def list(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.debug('Starting agents_service.list agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._lister.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=list")
            return {'message': str(exc)}

    def status(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.debug('Starting agents_service.status agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._status.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=status")
            return {'message': str(exc)}

    def tools(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.debug('Starting agents_service.tools agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._tools.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=tools")
            return {'message': str(exc)}

    def wakeup(self, flags: Mapping[str, Any] | None = None) -> dict[str, Any]:
        LOGGER.info('Starting agents_service.wakeup agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        try:
            flags = flags if flags is not None else {}
            return self._wakeup.execute(flags, self._create_context(flags))
        except Exception as exc:
            LOGGER.exception("Agent operation failed: operation=wakeup")
            return {'message': str(exc)}
