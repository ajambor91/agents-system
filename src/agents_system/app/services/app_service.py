from __future__ import annotations

import logging
from .asystem import Asystem
from .asystem_remote import AsystemRemote
from typing import TYPE_CHECKING, Any
from dataclasses import asdict
from shared.models.modules_list_data import ModulesListData
if TYPE_CHECKING:
    from _runtime.app import RuntimeApiWrapper
from lib.configuration import Configuration
from .modules_service import ModulesService
from ..exceptions.input_error import InputError
LOGGER = logging.getLogger(__name__)


class AppService:

    _asysten: Asystem
    _configuration: Configuration
    _runtime_api: RuntimeApiWrapper | None
    _module_service: ModulesService 
    def __init__(self, configuration: Configuration, runtime_api: RuntimeApiWrapper = None):
        self._module_service = ModulesService(configuration)
        self._configuration = configuration
        if runtime_api is not None:
            self._runtime_api = runtime_api
            self._asysten = AsystemRemote(self._module_service,runtime_api)
        else:
            self._asysten = Asystem(self._module_service)

    def execute(self, method_name: str, flags: dict[str,Any] = {},  module_name: str | None = None):
            LOGGER.info('Starting app_service.execute method_name=%s module_name=%s agent=%s dry_run=%s', method_name, module_name, (flags or {}).get('name'), (flags or {}).get('dry_run', False))
            if not module_name or module_name in ('agents_system', 'system'):
                action = getattr(self, method_name, None)
                if not callable(action):
                    return {"message": "Module does not have requested method"}
                return action(flags)
            if module_name and self._runtime_api:
                return self._asysten.exec(method_name,flags, module_name)
            
    def modules(self,flags: dict[str,Any]):
        LOGGER.debug('Starting app_service.modules agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        installed = flags.get('installed')
        running = flags.get('running') 
        if type(installed) is not bool or type(running) is not bool or installed == running:
            raise InputError(f"Wybierz dokładnie jedną flagę: --installed albo --running; wybrano installed: ${installed} oraz running: ${running}")
        
        modules: ModulesListData = self._asysten.modules(**flags)
        mode = "installed" if installed else "running"
        title = "Installed modules" if installed else "Running modules"
        names = [f"  {module.module_name}" for module in modules.modules.values()]
        message = title + ":\n" + ("\n".join(names) if names else "  (empty)")
        return {"mode": mode, "modules": asdict(modules)['modules'], "message": message}
    def logging(self, flags: dict[str, Any]):
        level = flags.get('level')
        LOGGER.debug(f"Starting app_service.logging selected level: {level}")
        return self._asysten.logging(level)

    def help(self,module_name: str, method_name: str): 
        if not module_name:
            return {"message": "Module does not have requested method"}
            
        if module_name and self._runtime_api:
            return self._asysten.help(module_name, method_name)

