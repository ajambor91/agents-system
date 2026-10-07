from __future__ import annotations
from typing import TYPE_CHECKING
from lib.modules_catalog import ModulesCatalog
if TYPE_CHECKING:
    from agents_system import (
        State as AgentsSystemsState
        )
class StateProvider:

    
    _agents_system_state: AgentsSystemsState | None = None

    def __init__(self,modules_catalog: ModulesCatalog):
        self._init_agents_system_state(modules_catalog)

    def get_agents_system_state(self):
        return self._agents_system_state

    def _init_agents_system_state(self, modules_catalog: ModulesCatalog):
        from agents_system import ( StateFactory as AgentsSystemStateFactory, 
        StateFactoryArg as AgentsSystemStateFactoryArg )
        self._agents_system_state = AgentsSystemStateFactory.create_state(
            AgentsSystemStateFactoryArg(
                modules_catalog=modules_catalog
            )
        )