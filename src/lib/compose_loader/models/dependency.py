from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingCollection, _MappingModel


@dataclass(slots=True)
class Dependency(_MappingModel):
    condition: str = "service_started"
    restart: bool = False
    required: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


class DependsOn(_MappingCollection[Dependency]):
    """Dependencies keyed by service name."""
