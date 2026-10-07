from typing import TYPE_CHECKING, Any
from .modules_service import ModulesService
from ..exceptions.input_error import InputError, ApiError
from shared.models.modules_list_data import ModulesListData

class Asystem:

    _modules_service: ModulesService
    def __init__(self, modules_service: ModulesService):
        self.modules_service = modules_service

    def exec(self, method_name: str, flags: dict[str,Any] = {},  module_name: str | None = None):
        raise InputError("Cannot get other's module in local mode")

    def help(self,module_name:str,method_name: str):
        raise InputError("Cannot get other's module help in local mode")
    
    def modules(self,installed: bool = False, running: bool = False) -> ModulesListData:
        if type(installed) is not bool or type(running) is not bool or installed == running:
            raise InputError("Wybierz dokładnie jedną flagę: --installed albo --running")
        if running:
            raise ApiError("Nie można pobrać modułów w trybie lokalnym")
        return self.modules_service.installed_reader.list_modules()
