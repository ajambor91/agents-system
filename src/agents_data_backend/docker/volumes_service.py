from docker.models.volumes import Volume
from .models.volume_candidate import VolumeCandidate
from lib.compose_loader.models import VolumeDefinitions
class VolumesService:

    def check_volumes_state(self, volumes_state: VolumeDefinitions, candidates: VolumeCandidate) -> dict[str, dict]:

        to_create: dict[str, dict] = {}
        to_check: dict[str, dict] = {}

        volumes = volume_definition.values()

        for volume in volumes:
            existing_volume = (
                self._candidates_service.get_existing_volume(volume.name)
            )
            if existing_volume is None:
                to_create[volume.name] = {
                    "def": volume
                }
                continue
            docker_volume = existing_volume.get_docker_volume()
            volume_definition = existing_volume.get_volume_definition()
            to_check[volume.name] = {
                "def": volume_definition,
                "obj": docker_volume
            }
        return {
            "to_create": to_create,
            "to_check": to_check
        }



    def is_managed_volume(
        self,
        volume: Volume,
        expected_hashkey: str
    ) -> bool:

        volume.reload()

        labels = volume.attrs.get("Labels") or {}

        hashkey = labels.get("com.agents-system.hashkey")

        if not hashkey:
            return False

        return hashkey == expected_hashkey