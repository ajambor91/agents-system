"""The modules command returns installed records or resident instances."""
from __future__ import annotations

import logging

from typing import Any

from lib.configuration import Configuration
from lib.modules_catalog import ModulesFactory, ModulesCatalog
from ..exceptions import InputError, ApiError
from .installed_modules import InstalledModulesReader


LOGGER = logging.getLogger(__name__)


class ModulesService:
    def __init__(self, configuration: Configuration) -> None:
        self.installed_reader = InstalledModulesReader(configuration)

    def list(self) -> list[dict[str, Any]]:
        
        LOGGER.debug('Starting modules_service.list')
        modules = self.installed_reader.list_modules()
        return modules
