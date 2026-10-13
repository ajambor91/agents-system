from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingModel


@dataclass(slots=True)
class Build(_MappingModel):
    context: str | None = None
    dockerfile: str | None = None
    target: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
