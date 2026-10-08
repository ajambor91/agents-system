from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from manifests.app.exceptions.manifest_validation_error import _read
from manifests.app.models.manifest_abc import ManifestModel


@dataclass(slots=True, kw_only=True)
class CommandInputModuleManifest(ManifestModel):
    source: str
    type: str
    maximum_bytes: int

    def _validate_content(self) -> None:
        self._str("source", self.source)
        self._str("type", self.type)
        self._type("maximum_bytes", self.maximum_bytes, int)
        if type(self.maximum_bytes) is int:
            def positive() -> None:
                if self.maximum_bytes <= 0:
                    raise ValueError("must be greater than zero")
            self._capture("maximum_bytes", positive)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CommandInputModuleManifest:
        return cls(
            source=_read(data, "source"),
            type=_read(data, "type"),
            maximum_bytes=_read(data, "maximum_bytes"),
        )