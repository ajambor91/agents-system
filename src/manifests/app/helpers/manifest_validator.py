"""Select validation behavior through registered strategies."""
from typing import Any, Iterable
from manifests.app.exceptions import ManifestStructureError, UnsupportedManifestKindError
from .manifests_validator.abstract import ManifestValidationStrategy
from .manifests_validator.environment import EnvironmentManifestValidationStrategy
from .manifests_validator.module import ModuleManifestValidationStrategy
from .manifests_validator.modules import ModulesManifestValidationStrategy


class ManifestValidator:
    _strategies = {
        strategy.kind: strategy
        for strategy in (
            ModulesManifestValidationStrategy(),
            ModuleManifestValidationStrategy(),
            EnvironmentManifestValidationStrategy(),
        )
    }

    @classmethod
    def validate(cls, data: dict[str, Any], *, strategies: Iterable[ManifestValidationStrategy] | None = None) -> bool:
        if not isinstance(data, dict):
            raise ManifestStructureError("Manifest musi być obiektem JSON")
        registry = cls._strategies if strategies is None else {strategy.kind: strategy for strategy in strategies}
        kind = data.get("kind")
        strategy = registry.get(kind) if isinstance(kind, str) else None
        if strategy is None:
            raise UnsupportedManifestKindError(f"Unsupported manifest kind: {kind}")
        model = strategy.create_model(data)
        model.validate()
        return True
