from __future__ import annotations
from typing import Any, TYPE_CHECKING
from .asystem import Asystem
if TYPE_CHECKING:
    from _runtime.app import RuntimeApiWrapper

from .modules_service import ModulesService
from ..state import AppStateRemote, State
from ..exceptions.input_error import InputError
from shared.models.modules_list_data import ModulesListData
class AsystemRemote(Asystem):

    _runtime_api_wrapper: RuntimeApiWrapper | None = None
    def __init__(self, modules_service: ModulesService, runtime_api_wrapper: RuntimeApiWrapper):
        super().__init__(modules_service)
        self._runtime_api_wrapper = runtime_api_wrapper
  


    def exec(self, method_name: str, flags: dict[str,Any] = {},  module_name: str | None = None):
        module = self._runtime_api_wrapper.instance(module_name)
        
        if not module:
            raise InputError("Cannot find requested module")
        action = getattr(module, 'execute', None)
        if not callable(action):
            raise Exception("Module does not have requested method")
        return action(method_name, flags, module_name)

    def help(self,module_name:str,method_name: str):
        module = self._runtime_api_wrapper.instance(module_name)
        
        if not module:
            raise InputError("Cannot find requested module")
        action = getattr(module, 'help', None)
        if not callable(action):
            raise Exception("Module does not have requested method")
        return action(method_name)
        
    def modules(self, installed: bool = False, running: bool = False) -> ModulesListData:
        if type(installed) is not bool or type(running) is not bool or installed == running:
            raise InputError("Wybierz dokładnie jedną flagę: --installed albo --running")
        if running:
            return self._runtime_api_wrapper.get_running_modules()
        return super().modules(installed=installed, running=running)

    
