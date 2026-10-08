from ..ports import AgentRuntimeInstall
from ..ports import AgentRuntimeRemove
from lib.configuration import Configuration
from ..open_claw import OpenClawFacade
class OpenClawRuntime(AgentRuntimeInstall, AgentRuntimeRemove):
    _configuration: Configuration
    _openclaw_facade: OpenClawFacade
    def __init__(self, configuration: Configuration):
        super().__init__()
        self._configuration = configuration
        self._openclaw_facade = OpenClawFacade()


    def add_agent(self, agent_name: str, agent_home: str, agent_model: str, force: bool):
        return self._openclaw_facade.add_agent(agent_name, agent_home, agent_model, force)

    def remove_agent(self, agent_name: str):
        return self._openclaw_facade.remove_agent(agent_name)