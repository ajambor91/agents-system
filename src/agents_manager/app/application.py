"""Composition root and public API for Agents Manager."""
from __future__ import annotations

import logging

from typing import Any

from lib.configuration import Configuration
from .services import (
    AppService,
    HelpService,
)


LOGGER = logging.getLogger(__name__)


class AgentsApplication:
    _help_service: HelpService
    _app_service: AppService
    def __init__(
        self,
        configuration: Configuration,
        manifests: dict[str, Any] | None = None
    ) -> None:
        self._help_service = HelpService(manifests)
        self._app_service = AppService(configuration) 

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
        return self._app_service.exec(method_name, flags)
    
    def connect_agents_runtime(self,args: dict[str,Any] = {}) -> dict[str, Any]:
        return self._app_service.connect_agents_runtime()
    
