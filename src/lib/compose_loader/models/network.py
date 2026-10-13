from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingCollection, _MappingModel


@dataclass(slots=True)
class Network(_MappingModel):
    name: str | None = None
    driver: str | None = None
    external: bool | dict[str, Any] = False
    internal: bool = False
    attachable: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class Networks(_MappingCollection[Network]):
    """Top-level networks, keyed by Compose name."""


@dataclass(slots=True)
class ServiceNetwork(_MappingModel):
    aliases: list[str] = field(default_factory=list)
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ServiceNetworks(_MappingCollection[ServiceNetwork]):
    """Service network attachments, keyed by network name."""
