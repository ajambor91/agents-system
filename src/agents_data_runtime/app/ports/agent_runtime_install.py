from abc import ABC, abstractmethod
class AgentRuntimeInstall(ABC):

    @abstractmethod
    def add_agent(self, agent_name: str, agent_home: str, agent_model: str, force: bool):
        pass
