"""Public API of the Agents System module."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .state.app_state_remote import AppStateRemote, State
from .services.app_service import AppService
if TYPE_CHECKING:
    from _runtime.app import RuntimeApiWrapper

from lib.configuration import Configuration
from .services import HelpService

class Application:
    _configuration: Configuration 
    _app_service: AppService 
    _help_service: HelpService
    _runtime_api_wrapper: RuntimeApiWrapper | None = None

    def __init__(self, configuration: Configuration, manifests: dict[str, Any] = {}) -> None:
        self._configuration = configuration
        self._help_service = HelpService(manifests)
        self._app_service = AppService(self._configuration)


    def execute(self, method_name: str, flags: dict[str, Any] = {},  module_name: str | None = None) -> dict[str, Any]:
        """Return installed module records or public resident instances."""
        return self._app_service.execute(method_name, flags, module_name)
        return self._app_service.list(installed=installed, running=running)

    def help(self, method_name: str, flags: dict[str, Any] = {}, module_name: str | None = None) -> dict[str, Any]:
        """Return installed module records or public resident instances."""
        if module_name is None or module_name in {"agents_system", "system"}:
             return self._help_service.help(method_name)
        return self._app_service.help(module_name, method_name)
    def initialize(self, runtime_api: RuntimeApiWrapper):
            self._runtime_api_wrapper = runtime_api
            self._app_service = AppService(self._configuration, runtime_api)
            initial_state: State = runtime_api.request_agents_systeninitial_stateget_agents_system_state()
            AppStateRemote.init_state(initial_state, True)
        
        

        