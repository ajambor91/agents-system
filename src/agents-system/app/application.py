"""Public API of the Agents System module."""
from __future__ import annotations

from typing import Any

from lib.configuration import Configuration
from .services.modules import ModulesService


class Application:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        self.modules_service = ModulesService(configuration)

    def modules(self, *, installed: bool = False, running: bool = False) -> dict[str, Any]:
        """Return installed module records or public resident instances."""
        return self.modules_service.list(installed=installed, running=running)
