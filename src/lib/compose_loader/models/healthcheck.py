from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingModel


@dataclass(slots=True)
class Healthcheck(_MappingModel):
    test: str | list[str] | None = None
    interval: str | None = None
    timeout: str | None = None
    retries: int | None = None
    start_period: str | None = None
    start_interval: str | None = None
    disable: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
