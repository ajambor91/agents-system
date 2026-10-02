"""The modules command returns installed records or resident instances."""
from __future__ import annotations

from typing import Any

from lib.configuration import Configuration
from ..exceptions import InputError
from .installed_modules import InstalledModulesReader
from .runtime_modules import RuntimeModulesClient


class ModulesService:
    def __init__(self, configuration: Configuration) -> None:
        self.installed_reader = InstalledModulesReader(configuration)
        self.runtime_client = RuntimeModulesClient(configuration)

    def list(self, *, installed: bool = False, running: bool = False) -> dict[str, Any]:
        if type(installed) is not bool or type(running) is not bool or installed == running:
            raise InputError("Wybierz dokładnie jedną flagę: --installed albo --running")
        modules = self.installed_reader.list_modules() if installed else self.runtime_client.list_modules()
        mode = "installed" if installed else "running"
        title = "Installed modules" if installed else "Running modules"
        names = [f"  {module['name']}" for module in modules]
        message = title + ":\n" + ("\n".join(names) if names else "  (empty)")
        return {"mode": mode, "modules": modules, "message": message}
