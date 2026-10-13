
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


class CandidatesService:
    _candidates_state: CandidatesState
    _compose_state: ComposeState
    _docker_client: docker.DockerClient
    def __init__(self, 
                 compose_state: ComposeState,
                 docker_client: docker.DockerClient
                 ):
        self._candidates_state = CandidatesState.createState()
        self._compose_state = compose_state
        self._docker_client = docker_client
        self.__initialize()

    @property
    def candidates_state(self) -> CandidatesState:
        return self._compose_state

    def __initialize(self) -> None:
        self._get_existing_containers()
        self._get_existing_volumes()
        self._get_existing_networks()
        self._get_existing_images()

    # ============================
    # CONTAINERS
    # ============================

    def _get_existing_containers(self) -> None:
        for service in self._compose_state.compose_data.services.items():
            self._get_existing_container(service)

    def _get_existing_container(
        self,
        service: tuple[str, ServiceYAML]
    ) -> Container | None:

        try:
            candidate = self._docker_client.containers.get(
                service[1].container_name
            )

        except NotFound:
            return None

        self._candidates_state.add_container(
            key=service[0],
            service=service[1],
            candidate=candidate
        )

        return candidate

    # ============================
    # VOLUMES
    # ============================

    def _get_existing_volumes(self) -> None:
        for volume in self._compose_state.compose_data.volumes:
            self._get_existing_volume(volume)

    def _get_existing_volume(
        self,
        volume: VolumeDefinitionYAML
    ) -> Volume | None:

        try:
            candidate = self._docker_client.volumes.get(
                volume.name
            )

        except NotFound:
            return None

        self._candidates_state.add_volume(
            key=volume.name,
            volume=volume,
            candidate=candidate
        )

        return candidate

    # ============================
    # NETWORKS
    # ============================

    def _get_existing_networks(self) -> None:
        for network in self._compose_state.compose_data.networks:
            self._get_existing_network(network)

    def _get_existing_network(
        self,
        network: NetworkYAML
    ) -> Network | None:

        try:
            candidate = self._docker_client.networks.get(
                network.name
            )

        except NotFound:
            return None

        self._candidates_state.add_network(
            key=network.name,
            network=network,
            candidate=candidate
        )

        return candidate

    # ============================
    # IMAGES
    # ============================

    def _get_existing_images(self) -> None:
        for service in self._compose_state.compose_data.services.items():
            self._get_existing_image(service)

    def _get_existing_image(
        self,
        service: tuple[str, ServiceYAML]
    ) -> Image | None:

        image_name = service[1].image

        if not image_name:
            return None

        try:
            candidate = self._docker_client.images.get(
                image_name
            )

        except NotFound:
            return None

        self._candidates_state.add_image(
            key=service[0],
            service=service[1],
            candidate=candidate
        )

        return candidate