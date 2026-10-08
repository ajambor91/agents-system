from typing import Any
from manifests.app.models.modules.module_manifest import ModuleManifest
from .abstract import ManifestValidationStrategy


class ModuleManifestValidationStrategy(ManifestValidationStrategy):
    kind = 'module-manifest'

    def create_model(self, data: dict[str, Any]) -> ModuleManifest:
        return ModuleManifest.from_dict(data)
