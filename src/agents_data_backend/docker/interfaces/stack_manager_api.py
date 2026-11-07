from abc import ABC, abstractmethod
import docker


class StackManagerApi(ABC):

    @property
    @abstractmethod
    def docker_client(self) -> docker.DockerClient:
        pass

    @property
    @abstractmethod
    def docker_compose_file(self) -> str:
        pass