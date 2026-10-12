from abc import ABC, abstractmethod
class AgentRuntimeRun(ABC):

    @abstractmethod
    def run_agent(self, agent_name: str, message: str, timeout: int = 0) -> str:
        pass