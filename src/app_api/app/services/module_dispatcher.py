"""Invoke a public application method through runtime or locally."""
from __future__ import annotations

import keyword
from typing import Any

from lib.configuration import Configuration
from ..exceptions import ApiError
from .module_loader import ModuleLoader
from .runtime import RuntimeDispatcher, RuntimeUnavailableError


class ModuleDispatcher:
    def __init__(self, configuration: Configuration) -> None:
        self.runtime = RuntimeDispatcher(configuration)
        self.loader = ModuleLoader(configuration)
        self._runtime_available: bool | None = None

    @property
    def runtime_available(self) -> bool:
        if self._runtime_available is None:
            self._runtime_available = self.runtime.is_available()
        return self._runtime_available

    def dispatch(
        self, section: dict[str, Any], command: dict[str, Any], arguments: dict[str, Any]
    ) -> Any:
        method = command.get("method", command["name"].replace("-", "_"))
        if not isinstance(method, str) or not method.isidentifier() or method.startswith("_") or keyword.iskeyword(method):
            raise ApiError(f"Nieprawidłowa publiczna metoda: {method}")
        if self.runtime_available:
            try:
                return self.runtime.call(section["module_name"], method, arguments)
            except RuntimeUnavailableError:
                # No request was sent: local execution is safe.
                self._runtime_available = False
        instance = self.loader.load(section)
        action = getattr(instance, method, None)
        if not callable(action):
            raise ApiError(
                f"Moduł {section['module_name']} nie udostępnia metody {method}", exit_code=1
            )
        try:
            return action(**arguments)
        except Exception as exc:
            raise ApiError(
                f"Błąd {section['module_name']}.{method}: {exc}", exit_code=getattr(exc, "exit_code", 1)
            ) from exc
