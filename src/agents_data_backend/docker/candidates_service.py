from __future__ import annotations

from lib.compose_loader import (
    VolumeDefinition as VolumeDefinitionYAML,
    Service as ServiceYAML,
    Network as NetworkYAML,
)

from .candidates_state import CandidatesState

from .models.container_candidate import ContainerCandidate
from .models.volume_candidate import VolumeCandidate
from .models.network_candidate import NetworkCandidate
from .models.image_candidate import ImageCandidate

from .interfaces import (
    CandidatesStateService,
    CandidatesInternal,
    DockerUnitsApi,
    ComposeApi,
)


class CandidatesService(CandidatesStateService, CandidatesInternal):

    _docker_units: DockerUnitsApi
    _compose_service: ComposeApi
    _candidates_state: CandidatesState

    def __init__(self):
        self._candidates_state = CandidatesState.createState()

    @property
    def candidates_state(self) -> CandidatesState:
        return self._candidates_state

    def initialize(self, **kwargs) -> None:
        docker_units = kwargs.get("docker_units")
        compose_service = kwargs.get("compose_service")

        if not isinstance(docker_units, DockerUnitsApi):
            raise TypeError("Invalid DockerUnitsApi")

        if not isinstance(compose_service, ComposeApi):
            raise TypeError("Invalid ComposeApi")

        self._docker_units = docker_units
        self._compose_service = compose_service

    # ============================
    # STATE
    # ============================

    def create_existing_state(self) -> None:
        self.create_existing_containers()
        self.create_existing_volumes()
        self.create_existing_networks()
        self.create_existing_images()

    def get_existing_state(self) -> CandidatesState:
        return self._candidates_state

    # ============================
    # CONTAINERS
    # ============================

    def create_existing_containers(self) -> None:
        services = self._compose_service.compose_state.services

        for service in services.items():
            self.create_existing_container(service)

    def create_existing_container(
        self,
        service: tuple[str, ServiceYAML]
    ) -> None:

        candidate = self._docker_units.get_container(
            service[1].container_name
        )

        if candidate is None:
            return

        self._candidates_state.add_container(
            key=service[0],
            service=service[1],
            candidate=candidate
        )

    def get_existing_containers(
        self
    ) -> dict[str, ContainerCandidate]:
        return self._candidates_state.containers

    def get_existing_container(
        self,
        name: str
    ) -> ContainerCandidate | None:
        return self._candidates_state.get_container(name)

    # ============================
    # VOLUMES
    # ============================

    def create_existing_volumes(self) -> None:
        volumes = self._compose_service.compose_state.volumes

        for volume in volumes:
            self.create_existing_volume(volume)

    def create_existing_volume(
        self,
        volume: VolumeDefinitionYAML
    ) -> None:

        candidate = self._docker_units.get_volume(volume.name)

        if candidate is None:
            return

        self._candidates_state.add_volume(
            key=volume.name,
            volume=volume,
            candidate=candidate
        )

    def get_existing_volumes(
        self
    ) -> dict[str, VolumeCandidate]:
        return self._candidates_state.volumes

    def get_existing_volume(
        self,
        name: str
    ) -> VolumeCandidate | None:
        return self._candidates_state.get_volume(name)

    # ============================
    # NETWORKS
    # ============================

    def create_existing_networks(self) -> None:
        networks = self._compose_service.compose_state.networks

        for network in networks:
            self.create_existing_network(network)

    def create_existing_network(
        self,
        network: NetworkYAML
    ) -> None:

        candidate = self._docker_units.get_network(network.name)

        if candidate is None:
            return

        self._candidates_state.add_network(
            key=network.name,
            network=network,
            candidate=candidate
        )

    def get_existing_networks(
        self
    ) -> dict[str, NetworkCandidate]:
        return self._candidates_state.networks

    def get_existing_network(
        self,
        name: str
    ) -> NetworkCandidate | None:
        return self._candidates_state.get_network(name)

    # ============================
    # IMAGES
    # ============================

    def create_existing_images(self) -> None:
        services = self._compose_service.compose_state.services

        for service in services.items():
            self.create_existing_image(service)

    def create_existing_image(
        self,
        service: tuple[str, ServiceYAML]
    ) -> None:

        image_name = service[1].image

        if not image_name:
            return

        candidate = self._docker_units.get_image(image_name)

        if candidate is None:
            return

        self._candidates_state.add_image(
            key=service[0],
            service=service[1],
            candidate=candidate
        )

    def get_existing_images(
        self
    ) -> dict[str, ImageCandidate]:
        return self._candidates_state.images

    def get_existing_image(
        self,
        name: str
    ) -> ImageCandidate | None:
        return self._candidates_state.get_image(name)