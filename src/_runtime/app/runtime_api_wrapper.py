from __future__ import annotations

import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .instance_manager import InstanceManager
from .state_provider import StateProvider 
from shared.models.modules_list_data import ModuleData, ModulesListData

LOGGER = logging.getLogger(__name__)


class RuntimeApiWrapper:
    def __init__(self, instance_manager: InstanceManager,state_provider: StateProvider):
        self._instance_manager = instance_manager
        self._state_provider = state_provider

    def instance(self,module_name: str): 
        LOGGER.debug("Resolving managed runtime instance: module=%s", module_name)
        return self._instance_manager.get(module_name).instance_object

    def get_running_modules(self) -> ModulesListData:
        instances = self._instance_manager.list_managed_instances()
        state = self._state_provider.get_agents_system_state()
        modules = state.modules if state is not None else {}
        return ModulesListData(modules={
            item.get_class_name(): ModuleData(
                module_name=item.get_class_name(),
                reunning=True,
                description=modules[item.get_class_name()].description
                if item.get_class_name() in modules else "",
            )
            for item in sorted(instances, key=lambda item: item.get_class_name())
        })

    
    
    def request_agents_systeninitial_stateget_agents_system_state(self):
        return self._state_provider.get_agents_system_state()
