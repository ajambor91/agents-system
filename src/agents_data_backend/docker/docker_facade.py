from lib.compose_loader import ComposeLoader, ComposeData
from interfaces import (
    DockerManager, CandidatesApi, ComposeApi, DockerUnitsApi, StackManagerApi
)

class DockerFacade(DockerManager):

    _candidates: CandidatesApi
    _compose: ComposeApi
    _stack_manager: StackManagerApi
    _docker_units_service: DockerUnitsApi
    def __init__(self,
                candidates: CandidatesApi,
                compose: ComposeApi,
                stack_manager: StackManagerApi,
                docker_units_service: DockerUnitsApi
                ):
        self._candidates = candidates


