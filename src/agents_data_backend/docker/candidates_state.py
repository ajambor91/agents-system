from __future__ import annotations

from lib.compose_loader import Service, VolumeDefinition, Network as NetworkYAML
from .models.container_candidate import ContainerCandidate
from .models.volume_candidate import VolumeCandidate
from .models.network_candidate import NetworkCandidate
from .models.image_candidate import ImageCandidate

from docker.models.containers import Container
from docker.models.volumes import Volume
from docker.models.networks import Network
from docker.models.images import Image


class CandidatesState:
    _token = object()
    _instance: CandidatesState | None = None

    def __new__(cls, token: object) -> CandidatesState:
        if token is not cls._token:
            raise RuntimeError(
                "Cannot create instance from the outside"
            )

        if cls._instance is not None:
            raise RuntimeError(
                "CandidatesState is singleton, "
                "you can only create one instance"
            )

        instance = super().__new__(cls)
        cls._instance = instance

        return instance

    def __init__(self, token: object) -> None:
        self._containers: dict[str, ContainerCandidate] = {}
        self._volumes: dict[str, VolumeCandidate] = {}
        self._networks: dict[str, NetworkCandidate] = {}
        self._images: dict[str, ImageCandidate] = {}

    def add_container(
        self,
        key: str,
        candidate: Container,
        service: Service
    ) -> None:
        self._containers[key] = ContainerCandidate(
            service=service,
            container_candidate=candidate
        )

    def get_container(
        self,
        key: str
    ) -> ContainerCandidate | None:
        return self._containers.get(key)

    def add_volume(
        self,
        key: str,
        candidate: Volume,
        volume: VolumeDefinition
    ) -> None:
        self._volumes[key] = VolumeCandidate(
            volume=volume,
            volume_candidate=candidate
        )

    def get_volume(
        self,
        key: str
    ) -> VolumeCandidate | None:
        return self._volumes.get(key)

    def add_network(
        self,
        key: str,
        candidate: Network,
        network: NetworkYAML
    ) -> None:
        self._networks[key] = NetworkCandidate(
            network=network,
            network_candidate=candidate
        )

    def get_network(
        self,
        key: str
    ) -> NetworkCandidate | None:
        return self._networks.get(key)

    def add_image(
        self,
        key: str,
        candidate: Image,
        service: Service
    ) -> None:
        self._images[key] = ImageCandidate(
            service=service,
            image_candidate=candidate
        )

    def get_image(
        self,
        key: str
    ) -> ImageCandidate | None:
        return self._images.get(key)

    @classmethod
    def createState(cls) -> CandidatesState:
        if cls._instance is None:
            cls(cls._token)

        return cls._instance
