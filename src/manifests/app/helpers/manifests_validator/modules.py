from typing import Any
from manifests.app.models.modules.modules_manifest_module_manifest import ModulesManifestModuleManifest
from .abstract import ManifestValidationStrategy


class ModulesManifestValidationStrategy(ManifestValidationStrategy):
    kind = 'agents-system-modules-manifest'

    def create_model(self, data: dict[str, Any]) -> ModulesManifestModuleManifest:
        return ModulesManifestModuleManifest.from_dict(data)
