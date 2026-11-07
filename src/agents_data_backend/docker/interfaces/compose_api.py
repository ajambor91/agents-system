from abc import ABC, abstractmethod

class ComposeApi(ABC):



    @abstractmethod
    def check_current_state(self) -> None:
        pass