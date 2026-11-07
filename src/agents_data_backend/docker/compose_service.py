
from .compose_state import ComposeState
from .interfaces import (
    ComposeStateService, 
    DockerUnitsApi,
    CandidatesApi,
    ComposeInternal
    )
from pathlib import Path
from typing import Any
from .volumes_service import VolumesService
from .networks_service import NetworksService
from .containers_service import ContainersService
class ComposeService(ComposeStateService, ComposeInternal): 
    _compose_state: ComposeState | None = None
    _candidates_service: CandidatesApi | None = None
    _networks_service: NetworksService | None = None
    _containers_service: ContainersService | None = None
    _volumes_service: VolumesService | None = None
    def initialize(self, **kwargs):
        path = kwargs.get('path')
        candidates = kwargs.get('candidates_service')
        networks_service = kwargs.get('networks_service')
        volumes_service = kwargs.get('volumes_service')
        containers_service = kwargs.get('containers_service')
        if not isinstance(path, str) or not isinstance(candidates, CandidatesApi) or not isinstance(networks_service, NetworksService) or not isinstance(volumes_service, VolumesService) or not isinstance(containers_service, ContainersService):
            raise Exception("Invalid docker_compose file path, ContainersService, NetworksService, VolumesService or CandidatesApi") 
        self._compose_state = ComposeState.createState(Path(path).absolute())
        self._candidates_service = candidates
        self._networks_service = networks_service
        self._containers_service = containers_service
        self._volumes_service = volumes_service
    @property
    def compose_state(self) -> ComposeState:
        return self._compose_state

    @property
    def _compose_state_internal(self) -> ComposeState:
        if not isinstance(self._compose_state):
            raise Exception("Compose state not initialized")
        return self._compose_state

    def check_current_state(self):
        networks = self._networks_service.check_networks_state(
            self.compose_state.compose_data.networks,
            self._candidates_service.get_existing_networks()
            )
        volumes = self._volumes_service.check_volumes_state(
            self.compose_state.compose_data.volumes,
            self._candidates_service.get_existing_volumes()
        )
        containers = self._containers_service.check_containers_state(
            self.compose_state.compose_data.services,
            self._candidates_service.get_existing_containers())
        images =self._containers_service.check_images_state(
            [item.image
             for item in self.compose_state.compose_data.services.values()],
             self._candidates_service.get_existing_images()
        )

        to_create: dict[str, dict] = {
            'containers': containers['to_create'],
            'networks': networks['to_create'],
            'volumes' : volumes['to_create'],
            'images':images['to_create']
        }

        to_check: dict[str, dict] = {
            'containers': containers['to_check'],
            'networks': networks['to_check'],
            'volumes' : volumes['to_check'],
            'images':images['to_check']
        }


