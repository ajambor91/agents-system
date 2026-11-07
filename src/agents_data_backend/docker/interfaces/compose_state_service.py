
from abc import ABC, abstractmethod
from ..compose_state import ComposeData

class ComposeStateService(ABC):
    @property
    @abstractmethod
    def compose_state(self) -> ComposeData:
        pass