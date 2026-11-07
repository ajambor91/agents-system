from lib.compose_loader import Network as NetworkYAML
from docker.models.networks import Network


class NetworkCandidate:
    _docker_network: Network
    _network: NetworkYAML

    def __init__(self, *, network_candidate: Network, network: NetworkYAML):
        self._docker_network = network_candidate
        self._network = network

    def get_docker_network(self) -> Network:
        return self._docker_network

    def get_network_definition(self) -> NetworkYAML:
        return self._network