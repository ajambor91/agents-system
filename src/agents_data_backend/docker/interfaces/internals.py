from abc import ABC, abstractmethod
from .candidates_api import CandidatesApi
from .compose_api import ComposeApi
from .docker_units_api import DockerUnitsApi


class Initializer(ABC):

    @abstractmethod
    def initialize(self, **kwargs) -> None:
        pass


class CandidatesInternal(CandidatesApi, Initializer):
    pass


class ComposeInternal(ComposeApi, Initializer):
    pass



class DockerUnitsInternal(DockerUnitsApi, Initializer):
    pass