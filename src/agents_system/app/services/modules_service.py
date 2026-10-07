"""The modules command returns installed records or resident instances."""
from __future__ import annotations

from typing import Any

from lib.configuration import Configuration
from lib.modules_catalog import ModulesFactory, ModulesCatalog
from ..exceptions import InputError, ApiError
from .installed_modules import InstalledModulesReader


class ModulesService:
    def __init__(self, configuration: Configuration) -> None:
        self.installed_reader = InstalledModulesReader(configuration)

    def list(self) -> list[dict[str, Any]]:
        
        modules = self.installed_reader.list_modules()
        return modules
