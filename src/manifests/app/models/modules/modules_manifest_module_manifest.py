from __future__ import annotations

from lib.manifests_loader import ManifestsLoader
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from manifests.app.enums.manifest_kinds import ManifestKind
from manifests.app.exceptions.manifest_validation_error import _parse_list, _read
from manifests.app.models.manifest_abstract import Manifest
from manifests.app.models.modules.module_entry_module_manifest import (
    ModuleEntryModuleManifest,
)

@dataclass(slots=True, kw_only=True)
class ModulesManifestModuleManifest(Manifest):
    app_module_name: str
    manifest_absolute_path: str
    absolute_path: str
    app_dir: str
    children: list[ModuleEntryModuleManifest]

    def _validate_content(self) -> None:
        def check_kind() -> None:
            if isinstance(self.kind, ManifestKind) and self.kind is not ManifestKind.AGENTS_SYSTEM_MODULES:
                raise ValueError("kind does not match ModulesManifestModuleManifest")

        self._capture("kind", check_kind)
        self._str("app_module_name", self.app_module_name)
        self._str("manifest_absolute_path", self.manifest_absolute_path)
        self._str("absolute_path", self.absolute_path)
        self._str("app_dir", self.app_dir)
        self._nested_list("children", self.children, ModuleEntryModuleManifest)
        
        if type(self.children) is list:
            seen: dict[str, int] = {}
            for index, item in enumerate(self.children):
                if not isinstance(item, ModuleEntryModuleManifest) or type(item.module_name) is not str:
                    continue
                if item.module_name in seen:
                    earlier = seen[item.module_name]

                    def duplicate(name=item.module_name, earlier=earlier) -> None:
                        raise ValueError(f"duplicate module_name {name!r}; first occurrence at index {earlier}")

                    self._capture(f"children[{index}].module_name", duplicate)
                else:
                    seen[item.module_name] = index

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModulesManifestModuleManifest:
        """Construct nested models without validation (even for bad field values)."""
        if not isinstance(data, Mapping):
            raise TypeError("manifest JSON root must be an object")
        raw_kind = _read(data, "kind")
        if type(raw_kind) is str:
            try:
                raw_kind = ManifestKind(raw_kind)
            except ValueError:
                pass  # retain unsupported kind so validate() can report it
        return cls(
            schema_version=_read(data, "schema_version"),
            version=_read(data, "version"),
            kind=raw_kind,
            app_module_name=_read(data, "app_module_name"),
            manifest_absolute_path=_read(data, "manifest_absolute_path"),
            absolute_path=_read(data, "absolute_path"),
            app_dir=_read(data, "app_dir"),
            children=_parse_list(_read(data, "children"), ModuleEntryModuleManifest),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> ModulesManifestModuleManifest:
        """Parsing errors (JSON syntax/I/O) surface immediately; schema errors wait."""
        return cls.from_dict(ManifestsLoader.load_manifest(path))