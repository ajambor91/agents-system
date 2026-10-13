from lib.compose_loader import VolumeDefinition
from docker.models.volumes import Volume


class VolumeCandidate:
    _docker_volume: Volume
    _volume: VolumeDefinition

    def __init__(self, *, volume_candidate: Volume, volume: VolumeDefinition):
        self._docker_volume = volume_candidate
        self._volume = volume
