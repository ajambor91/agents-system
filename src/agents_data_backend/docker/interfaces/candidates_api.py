from abc import ABC, abstractmethod

from agents_data_backend.docker.candidates_state import (
    CandidatesState,
    ImageCandidate,
    ContainerCandidate,
    VolumeCandidate,
    NetworkCandidate
    )
from lib.compose_loader import (
    Service as ServiceYAML,
    VolumeDefinition as VolumeDefinitionYAML,
    Network as NetworkYAML,
)


class CandidatesApi(ABC):

    # ============================
    # STATE
    # ============================

    @abstractmethod
    def create_existing_state(self) -> None:
        pass

    @abstractmethod
    def get_existing_state(self) -> CandidatesState:
        pass

    # ============================
    # CONTAINERS
    # ============================

    @abstractmethod
    def create_existing_containers(self) -> None:
        pass

    @abstractmethod
    def create_existing_container(
        self,
        service: tuple[str, ServiceYAML]
    ) -> None:
        pass

    @abstractmethod
    def get_existing_containers(
        self
    ) -> dict[str, ContainerCandidate]:
        pass

    @abstractmethod
    def get_existing_container(
        self,
        name: str
    ) -> ContainerCandidate | None:
        pass

    # ============================
    # VOLUMES
    # ============================

    @abstractmethod
    def create_existing_volumes(self) -> None:
        pass

    @abstractmethod
    def create_existing_volume(
        self,
        volume: VolumeDefinitionYAML
    ) -> None:
        pass

    @abstractmethod
    def get_existing_volumes(
        self
    ) -> dict[str, VolumeCandidate]:
        pass

    @abstractmethod
    def get_existing_volume(
        self,
        name: str
    ) -> VolumeCandidate | None:
        pass

    # ============================
    # NETWORKS
    # ============================

    @abstractmethod
    def create_existing_networks(self) -> None:
        pass

    @abstractmethod
    def create_existing_network(
        self,
        network: NetworkYAML
    ) -> None:
        pass

    @abstractmethod
    def get_existing_networks(
        self
    ) -> dict[str, NetworkCandidate]:
        pass

    @abstractmethod
    def get_existing_network(
        self,
        name: str
    ) -> NetworkCandidate | None:
        pass

    # ============================
    # IMAGES
    # ============================

    @abstractmethod
    def create_existing_images(self) -> None:
        pass

    @abstractmethod
    def create_existing_image(
        self,
        service: tuple[str, ServiceYAML]
    ) -> None:
        pass

    @abstractmethod
    def get_existing_images(
        self
    ) -> dict[str, ImageCandidate]:
        pass

    @abstractmethod
    def get_existing_image(
        self,
        name: str
    ) -> ImageCandidate | None:
        pass