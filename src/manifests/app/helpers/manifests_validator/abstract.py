"""Strategies construct a model; validation belongs to that model."""
from abc import ABC, abstractmethod
from typing import Any
from manifests.app.models.manifest_abc import ManifestModel


class ManifestValidationStrategy(ABC):
    kind: str

    @abstractmethod
    def create_model(self, data: dict[str, Any]) -> ManifestModel:
        """Select and parse the model without performing validation."""
