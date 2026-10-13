from dataclasses import dataclass, field
from typing import Any
from ._mapping import _MappingCollection, _MappingModel, _SequenceCollection, _plain


@dataclass(slots=True)
class Volume(_MappingModel):
    target: str
    source: str | None = None
    type: str = "volume"
    read_only: bool = False
    mode: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Volumes(_SequenceCollection[Volume]):
    """Ordered service mounts."""


@dataclass(slots=True)
class VolumeDefinition(_MappingModel):
    name: str | None = None
    driver: str | None = None
    driver_opts: dict[str, Any] = field(default_factory=dict)
    external: bool | dict[str, Any] = False
    labels: dict[str, Any] | list[str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_docker_kwargs(self, key: str) -> dict[str, Any]:
        """Build volumes.create kwargs using name or key, without project prefix.

        External volumes must be fetched with volumes.get instead of created.
        Only Docker SDK fields are included; no Docker dependency is required.
        """
        if self.external is not False:
            raise ValueError("External volumes must be fetched, not created")
        name = self.name if self.name is not None else key
        if not isinstance(name, str) or not name:
            raise ValueError("A non-empty volume name is required")
        result: dict[str, Any] = {"name": name}
        if self.driver is not None:
            result["driver"] = self.driver
        if self.driver_opts:
            result["driver_opts"] = _plain(self.driver_opts)
        if self.labels:
            if isinstance(self.labels, list):
                labels = {}
                for entry in self.labels:
                    label, separator, value = entry.partition("=")
                    labels[label] = value if separator else ""
                result["labels"] = labels
            else:
                result["labels"] = _plain(self.labels)
        return result


class VolumeDefinitions(_MappingCollection[VolumeDefinition]):
    """Top-level named volumes, keyed by Compose name."""
