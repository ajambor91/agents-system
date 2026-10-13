from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingCollection, _MappingModel

from .build import Build
from .dependency import DependsOn
from .environment import Environment
from .healthcheck import Healthcheck
from .network import ServiceNetworks
from .port import Ports
from .resource import ResourceReferences
from .volume import Volumes


@dataclass(slots=True)
class Service(_MappingModel):
    name: str
    image: str | None = None
    build: Build | None = None
    ports: Ports = field(default_factory=Ports)
    volumes: Volumes = field(default_factory=Volumes)
    environment: Environment = field(default_factory=Environment)
    depends_on: DependsOn = field(default_factory=DependsOn)
    networks: ServiceNetworks = field(default_factory=ServiceNetworks)
    secrets: ResourceReferences = field(default_factory=ResourceReferences)
    configs: ResourceReferences = field(default_factory=ResourceReferences)
    healthcheck: Healthcheck | None = None
    command: str | list[str] | None = None
    entrypoint: str | list[str] | None = None
    container_name: str | None = None
    restart: str | None = None
    profiles: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class Services(_MappingCollection[Service]):
    """Services keyed by Compose service name."""
