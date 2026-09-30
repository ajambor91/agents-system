from typing import Any

from manifests.app.models.modules.modules_manifest_module_manifest import ModulesManifestModuleManifest


class ManifestValidator:

    _models = {
        "agents-system-modules-manifest": ModulesManifestModuleManifest,
    }

    @staticmethod
    def validate(data: dict[str, Any]) -> bool:
        kind = data.get("kind")

        model_class = ManifestValidator._models.get(kind)

        if model_class is None:
            raise ValueError(
                f"Unsupported manifest kind: {kind}"
            )

        manifest = model_class.from_dict(data)

        manifest.validate()

        return True