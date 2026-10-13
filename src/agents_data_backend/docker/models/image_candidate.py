from lib.compose_loader import Service
from docker.models.images import Image


class ImageCandidate:
    _docker_image: Image
    _service: Service

    def __init__(self, *, image_candidate: Image, service: Service):
        self._docker_image = image_candidate
        self._service = service
