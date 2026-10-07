from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shared.exceptions.missing import _MISSING
from .module_manifest import ModuleManifest
from typing import Any, Mapping

from manifests.app.exceptions.manifest_validation_error import _parse_list, _read
from manifests.app.models.manifest_abc import ManifestModel
from manifests.app.models.modules.command_entry_module_manifest import (
    CommandEntryModuleManifest,
)


@dataclass(slots=True, kw_only=True)
class ModuleEntryModuleManifest(ManifestModel):
    section_name: str | None
    absolute_module_path: str
    is_menu_option: bool
    is_runtime: bool
    runtime: list[str]
    module_name: str
    menu_name: str | None
    description: str
    commands: list[CommandEntryModuleManifest]
    manifest_path: str | None = None

    @property
    def name(self) -> str:
        return self.module_name

    def _validate_content(self) -> None:
        if self.is_menu_option is True or self.section_name is not None:
            self._str("section_name", self.section_name)
        self._str("absolute_module_path", self.absolute_module_path)
        self._type("is_menu_option", self.is_menu_option, bool)
        self._type("is_runtime", self.is_runtime, bool)
        self._strings("runtime", self.runtime)
        self._str("module_name", self.module_name)
        if self.manifest_path is not None:
            self._str('manifest_path', self.manifest_path)
            def validate_reference():
                path = Path(self.manifest_path)
                if not path.is_absolute() or '..' in path.parts:
                    raise ValueError('manifest_path must be a safe absolute path')
                if any(value is not _MISSING for value in (self.menu_name, self.description, self.commands)):
                    raise ValueError('help fields must be declared only in the module manifest')
                model = ModuleManifest.from_json(path)
                self._nested('manifest', model)
                if model.module_name != self.module_name:
                    raise ValueError('module_name does not match the module reference')
                if self.is_menu_option is True:
                    self._str('manifest.menu_name', model.menu_name)
                    self._str('manifest.usage', model.usage)
            self._capture('manifest_path', validate_reference)
            return
        if self.is_menu_option is True or self.menu_name is not None:
            self._str("menu_name", self.menu_name)
        self._str("description", self.description)
        self._nested_list("commands", self.commands, CommandEntryModuleManifest)
        self._unique_names("commands", self.commands, CommandEntryModuleManifest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModuleEntryModuleManifest:
        return cls(
            manifest_path=data.get("manifest_path"),
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
