from __future__ import annotations

from typing import TYPE_CHECKING

from docker.models.networks import Network
from lib.compose_loader.models import Networks

if TYPE_CHECKING:
    from .interfaces.candidates_api import CandidatesApi


class NetworksService:
    def check_networks_state(
        self, networks_state: Networks, candidates: CandidatesApi
    ) -> dict[str, dict]:
        to_create: dict[str, dict] = {}
        to_check: dict[str, dict] = {}

        for network in networks_state.values():
            existing_network = candidates.get_existing_network(network.name)
            if existing_network is None:
                to_create[network.name] = {"def": network}
                continue
            to_check[network.name] = {
                "def": existing_network.get_network_definition(),
                "obj": existing_network.get_docker_network(),
            }

        return {"to_create": to_create, "to_check": to_check}

    def is_managed_network(
        self, network: Network, expected_hashkey: str
    ) -> bool:
        network.reload()
        labels = network.attrs.get("Labels") or {}
        hashkey = labels.get("com.agents-system.hashkey")
        return bool(hashkey) and hashkey == expected_hashkey
