from __future__ import annotations

from lib.compose_loader import (
    ComposeData,
    VolumeDefinition as VolumeDefinitionYAML,
    Service as ServiceYAML,
    Network as NetworkYAML,
    Volume as VolumeYAML
)

import docker

from docker.errors import NotFound
from docker.models.containers import Container
from docker.models.volumes import Volume
from docker.models.networks import Network
from docker.models.images import Image

from .compose_state import ComposeState
from .candidates_state import CandidatesState
from .candidates_service import CandidatesService
from .compose_service import ComposeService
from pathlib import Path


class StackManager:
    _DOCKER_FILES_DIR: str = 'docker_files'
    _COMPOSE_FILE_NAME: str = 'docker-compose.yml'

    _docker_client: docker.DockerClient
    _compose_service: ComposeService
    _candidates_service: CandidatesService

    def __init__(self):
        self._docker_client = docker.from_env()
        self._compose_service = ComposeService("%s/%s", self._DOCKER_FILES_DIR, self._COMPOSE_FILE_NAME)
        self._candidates_service = CandidatesService(
            compose_state=self._compose_service.compose_state,
            docker_client=self._docker_client
        )
       
    

    def create_volumes(self) -> None:
        volumes_defs = self._compose_state.compose_data.volumes

        for vol in volumes_defs:
            self._docker_client.volumes.create(name=vol.name)

    def create_networks(self) -> None:
        pass

    def create_services(self) -> None:
        pass

  