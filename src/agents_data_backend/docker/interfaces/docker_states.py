from abc import ABC, abstractmethod

import docker
from .compose_state_service import ComposeStateService
from .candidates_state_service import CandidatesStateService

class DockerStates(ABC):
    @property
    @abstractmethod
    def compose_service(self) -> ComposeStateService:
            pass
    
    @property
    @abstractmethod
    def candidates_service(self) -> CandidatesStateService:
          pass 

    @property
    @abstractmethod
    def docker_client(self) -> docker.DockerClient:
        pass
        