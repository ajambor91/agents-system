
import logging
import os
from typing import TYPE_CHECKING, Any
from .modules_service import ModulesService
from ..exceptions.input_error import InputError, ApiError
from shared.models.modules_list_data import ModulesListData

LOGGER = logging.getLogger(__name__)


class Asystem:

    _modules_service: ModulesService
    def __init__(self, modules_service: ModulesService):
        self.modules_service = modules_service

    def exec(self, method_name: str, flags: dict[str,Any] = {},  module_name: str | None = None):
        LOGGER.debug('Starting asystem.exec method_name=%s module_name=%s agent=%s dry_run=%s', method_name, module_name, (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        raise InputError("Cannot get other's module in local mode")

    def help(self,module_name:str,method_name: str):
        LOGGER.debug('Starting asystem.help module_name=%s method_name=%s', module_name, method_name)
        raise InputError("Cannot get other's module help in local mode")
    
    def modules(self,installed: bool = False, running: bool = False) -> ModulesListData:
        LOGGER.debug('Starting asystem.modules')
        if type(installed) is not bool or type(running) is not bool or installed == running:
            raise InputError("Wybierz dokładnie jedną flagę: --installed albo --running")
        if running:
            raise ApiError("Nie można pobrać modułów w trybie lokalnym")
        return self.modules_service.installed_reader.list_modules()

    def logging(self, level: str) -> dict[str, str]:
        os.environ['AGENTS_MANAGER_LOG_LEVEL'] = level
        return {'Current level': level}
        
