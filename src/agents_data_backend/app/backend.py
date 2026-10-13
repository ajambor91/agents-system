from typing import Any
from  lib.configuration import Configuration
from .services import (AppService, HelpService)
import logging
LOGGER = logging.getLogger(__name__)
class Backend:
    _help_service: HelpService
    _app_service: AppService
    def __init__(
        self,
        configuration: Configuration,
        manifests: dict[str, Any] | None = None):
        self._app_service = AppService
        self._help_service = HelpService

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