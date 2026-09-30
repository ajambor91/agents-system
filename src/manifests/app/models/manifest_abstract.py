from __future__ import annotations

from abc import ABC
from dataclasses import dataclass

from manifests.app.enums.manifest_kinds import ManifestKind
from manifests.app.exceptions.manifest_validation_error import _expected
from manifests.app.models.manifest_abc import ManifestModel

@dataclass(slots=True, kw_only=True)
class Manifest(ManifestModel, ABC):
    """Abstract parent of all manifest documents."""

    schema_version: int
    version: int
    kind: ManifestKind

    def _validate_common(self) -> None:
        """The abstract Manifest enforces the three required header fields."""
        self._type("schema_version", self.schema_version, int)
        self._type("version", self.version, int)
        self._capture("kind", lambda: _expected(self.kind, ManifestKind))