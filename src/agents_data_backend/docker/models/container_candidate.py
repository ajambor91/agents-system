from lib.compose_loader import Service
from docker.models.containers import Container


class ContainerCandidate:
    _docker_container: Container
    _service: Service

    def __init__(self, *, container_candidate: Container, service: Service):
        self._docker_container = container_candidate
        self._service = service