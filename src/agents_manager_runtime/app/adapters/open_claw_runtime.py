from ..ports import (AgentRuntimeInstall, AgentRuntimeRemove, AgentRuntimeRun)
from lib.configuration import Configuration
from ..open_claw import OpenClawFacade
from pathlib import Path
class OpenClawRuntime(AgentRuntimeInstall, AgentRuntimeRemove, AgentRuntimeRun):
    _configuration: Configuration
    _openclaw_facade: OpenClawFacade
    def __init__(self, configuration: Configuration):
        super().__init__()
        self._configuration = configuration
        self._openclaw_facade = OpenClawFacade()


    def add_agent(self, agent_name: str, agent_home: str, agent_model: str, force: bool) -> bool:
        return self._openclaw_facade.add_agent(agent_name, agent_home, agent_model, force)

    def remove_agent(self, agent_name: str) -> bool:
        return self._openclaw_facade.remove_agent(agent_name)

    def apply_identity(self, agent_name: str, agent_home: str) -> bool:
        return self._openclaw_facade.apply_identity(agent_name, agent_home)

    def run_agent(self, agent_name: str,message: str, timeout: int = 0) -> str:
        return self._openclaw_facade.run_agent(agent_name, message, timeout)
