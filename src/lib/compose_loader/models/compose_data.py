from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingModel

from .network import Networks
from .resource import Resources
from .service import Services
from .volume import VolumeDefinitions


@dataclass(slots=True)
class ComposeData(_MappingModel):
    services: Services = field(default_factory=Services)
    name: str | None = None
    version: str | None = None
    volumes: VolumeDefinitions = field(default_factory=VolumeDefinitions)
    networks: Networks = field(default_factory=Networks)
    secrets: Resources = field(default_factory=Resources)
    configs: Resources = field(default_factory=Resources)
    extra: dict[str, Any] = field(default_factory=dict)
