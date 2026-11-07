from __future__ import annotations

from typing import TYPE_CHECKING

from docker.models.containers import Container
from docker.models.images import Image
from lib.compose_loader.models import Services

if TYPE_CHECKING:
    from .interfaces.candidates_api import CandidatesApi


class ContainersService:
    def check_containers_state(
        self, services_state: Services, candidates: CandidatesApi
    ) -> dict[str, dict]:
        to_create: dict[str, dict] = {}
        to_check: dict[str, dict] = {}

        for name, service in services_state.items():
            existing_container = candidates.get_existing_container(name)
            if existing_container is None:
                to_create[name] = {"def": service}
                continue
            to_check[name] = {
                "def": existing_container.get_service(),
                "obj": existing_container.get_docker_container(),
            }

        return {"to_create": to_create, "to_check": to_check}

    def check_images_state(
        self, services_state: Services, candidates: CandidatesApi
    ) -> dict[str, dict]:
        to_create: dict[str, dict] = {}
        to_check: dict[str, dict] = {}

        for name, service in services_state.items():
            if not service.image:
                continue
            existing_image = candidates.get_existing_image(name)
            if existing_image is None:
                to_create[name] = {"def": service}
                continue
            to_check[name] = {
                "def": existing_image.get_service(),
                "obj": existing_image.get_docker_image(),
            }

        return {"to_create": to_create, "to_check": to_check}

    def is_managed_container(
        self, container: Container, expected_hashkey: str
    ) -> bool:
        container.reload()
        config = container.attrs.get("Config") or {}
        labels = config.get("Labels") or {}
        hashkey = labels.get("com.agents-system.hashkey")
        return bool(hashkey) and hashkey == expected_hashkey

    def is_managed_image(self, image: Image, expected_hashkey: str) -> bool:
        image.reload()
        config = image.attrs.get("Config") or {}
        labels = config.get("Labels") or {}
        hashkey = labels.get("com.agents-system.hashkey")
        return bool(hashkey) and hashkey == expected_hashkey
