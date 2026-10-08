from typing import Any
from manifests.app.consts import ENVIRONMENT_KIND
from manifests.app.models.environment import EnvironmentManifest
from .abstract import ManifestValidationStrategy


class EnvironmentManifestValidationStrategy(ManifestValidationStrategy):
    kind = ENVIRONMENT_KIND

    def create_model(self, data: dict[str, Any]) -> EnvironmentManifest:
        return EnvironmentManifest.from_dict(data)
