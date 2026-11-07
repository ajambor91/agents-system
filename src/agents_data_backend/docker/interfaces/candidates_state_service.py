from abc import ABC, abstractmethod
from ..candidates_state import CandidatesState

class CandidatesStateService(ABC):

    @property
    @abstractmethod
    def candidates_state(self) -> CandidatesState:
        pass