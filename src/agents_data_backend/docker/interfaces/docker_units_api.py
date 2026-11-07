from abc import ABC, abstractmethod

from docker.models.containers import Container
from docker.models.volumes import Volume
from docker.models.networks import Network
from docker.models.images import Image


class DockerUnitsApi(ABC):

    @abstractmethod
    def get_container(self, name: str) -> Container | None:
        pass

    @abstractmethod
    def get_volume(self, name: str) -> Volume | None:
        pass

    @abstractmethod
    def get_network(self, name: str) -> Network | None:
        pass

    @abstractmethod
    def get_image(self, name: str) -> Image | None:
        pass