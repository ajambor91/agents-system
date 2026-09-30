from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from manifests.app.exceptions.manifest_validation_error import _parse_list, _read
from manifests.app.models.manifest_abc import ManifestModel
from manifests.app.models.modules.command_entry_module_manifest import (
    CommandEntryModuleManifest,
)


@dataclass(slots=True, kw_only=True)
class ModuleEntryModuleManifest(ManifestModel):
    section_name: str
    absolute_module_path: str
    is_menu_option: bool
    is_runtime: bool
    runtime: list[str]
    module_name: str
    menu_name: str
    description: str
    commands: list[CommandEntryModuleManifest]

    @property
    def name(self) -> str:
        return self.module_name

    def _validate_content(self) -> None:
        self._str("section_name", self.section_name)
        self._str("absolute_module_path", self.absolute_module_path)
        self._type("is_menu_option", self.is_menu_option, bool)
        self._type("is_runtime", self.is_runtime, bool)
        self._strings("runtime", self.runtime)
        self._str("module_name", self.module_name)
        self._str("menu_name", self.menu_name)
        self._str("description", self.description)
        self._nested_list("commands", self.commands, CommandEntryModuleManifest)
        self._unique_names("commands", self.commands, CommandEntryModuleManifest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModuleEntryModuleManifest:
        return cls(
            section_name=_read(data, "section_name"),
            absolute_module_path=_read(data, "absolute_module_path"),
            is_menu_option=_read(data, "is_menu_option"),
            is_runtime=_read(data, "is_runtime"),
            runtime=_read(data, "runtime"),
            module_name=_read(data, "module_name"),
            menu_name=_read(data, "menu_name"),
            description=_read(data, "description"),
            commands=_parse_list(_read(data, "commands"), CommandEntryModuleManifest),
        )