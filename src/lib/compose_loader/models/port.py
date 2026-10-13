from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingModel, _SequenceCollection


@dataclass(slots=True)
class Port(_MappingModel):
    target: int | str
    published: int | str | None = None
    host_ip: str | None = None
    protocol: str = "tcp"
    mode: str | None = None
    name: str | None = None
    app_protocol: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Ports(_SequenceCollection[Port]):
    """Ordered port mappings; supports indexing and iteration."""
