from dataclasses import dataclass
from typing import Any
from ._mapping import _MappingCollection, _MappingModel


@dataclass(slots=True)
class EnvironmentVariable(_MappingModel):
    name: str
    value: str | int | float | bool | None = None


class Environment(_MappingCollection[EnvironmentVariable]):
    """Variables keyed by name; None means an unresolved value."""

    def to_mapping(self) -> dict[str, Any]:
        return {name: variable.value for name, variable in self.items()}
