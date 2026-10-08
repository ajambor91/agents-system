from abc import ABC, abstractmethod
class AgentRuntimeRemove(ABC):

    @abstractmethod
    def remove_agent(self, agent_name):
        pass