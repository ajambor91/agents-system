from __future__ import annotations
import docker

from .docker_units_service import DockerUnitsService
from .candidates_service import CandidatesService
from .compose_service import ComposeService
from pathlib import Path
from .interfaces import (
     StackManagerApi, Initializer
)

class StackManager(StackManagerApi, Initializer):
    _DOCKER_FILES_DIR: str = 'docker_files'
    _COMPOSE_FILE_NAME: str = 'docker-compose.yml'

    _docker_client: docker.DockerClient
    _compose_service: ComposeService | None = None
    _candidates_service: CandidatesService | None = None
    _docker_units_service: DockerUnitsService | None = None
    
    def __init__(self):
        self._docker_client = docker.from_env()

    def initialize(self, **kwargs):
        compose_service = kwargs.get('compose_service')
        candidates_service = kwargs.get('candidates_service')
        docker_unit_service = kwargs.get('docker_unit_service')
        if not isinstance(candidates_service, CandidatesService) or not isinstance(compose_service, ComposeService) or not isinstance(docker_unit_service, DockerUnitsService):
            raise Exception("Invalid CandidatesService, ComposeService and DockerUnitsService when initializing StackManager")

        self._docker_unit_service = docker_unit_service
        self._candidates_service = candidates_service
        self._compose_service = compose_service
       
    @property
    def docker_compose_file(self) -> str:
        return f"{self._DOCKER_FILES_DIR}/{self._COMPOSE_FILE_NAME}"


    @property
    def docker_client(self) -> docker.DockerClient:
        return self._docker_client


    def run(self):
        self._candidates_service.create_existing_state()
        state = self._candidates_service.get_existing_state()
    
   