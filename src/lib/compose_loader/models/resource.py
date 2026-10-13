from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingCollection, _MappingModel, _SequenceCollection


@dataclass(slots=True)
class Resource(_MappingModel):
    """Top-level secret or config definition."""

    name: str | None = None
    file: str | None = None
    environment: str | None = None
    external: bool | dict[str, Any] = False
    extra: dict[str, Any] = field(default_factory=dict)


class Resources(_MappingCollection[Resource]):
    """Secret or config definitions keyed by Compose name."""


@dataclass(slots=True)
class ResourceReference(_MappingModel):
    source: str
    target: str | None = None
    uid: str | None = None
    gid: str | None = None
    mode: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ResourceReferences(_SequenceCollection[ResourceReference]):
    """Service secret or config references."""
