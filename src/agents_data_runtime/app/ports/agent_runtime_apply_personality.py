from abc import ABC, abstractmethod

class AgentRuntimeApplyPersonality(ABC):

    @abstractmethod
    def apply_identity(self, agent_name: str, agent_home: str) -> bool:       
        pass
