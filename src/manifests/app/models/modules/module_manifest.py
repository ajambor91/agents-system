from __future__ import annotations
from dataclasses import dataclass
from lib.manifests_loader import ManifestsLoader
import re
from pathlib import Path
from typing import Any, Mapping

from manifests.app.enums.manifest_kinds import ManifestKind
from manifests.app.exceptions.manifest_validation_error import _read, _parse_list
from manifests.app.models.manifest_abstract import Manifest
from .command_entry_module_manifest import CommandEntryModuleManifest


@dataclass(slots=True, kw_only=True)
class ModuleManifest(Manifest):
    module_name: str
    menu_name: str | None
    description: str
    usage: str
    commands: list[CommandEntryModuleManifest]

    def _validate_content(self) -> None:
        def check_kind():
            if self.kind != ManifestKind.MODULE:
                raise ValueError('expected module-manifest')
        self._capture('kind', check_kind)
        def check_schema():
            if self.schema_version != 1:
                raise ValueError('expected schema_version=1')
        self._capture('schema_version', check_schema)
        self._str('module_name', self.module_name)
        def check_name():
            if isinstance(self.module_name, str) and not re.fullmatch(r'[a-z][a-z0-9_-]*', self.module_name):
                raise ValueError('invalid module_name')
        self._capture('module_name', check_name)
        def check_version():
            if type(self.version) is int and self.version < 1:
                raise ValueError('version must be a positive integer')
        self._capture('version', check_version)
        self._str('description', self.description)
        if self.menu_name is not None:
            self._str('menu_name', self.menu_name)
        self._type('usage', self.usage, str)
        self._nested_list('commands', self.commands, CommandEntryModuleManifest)
        self._unique_names('commands', self.commands, CommandEntryModuleManifest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModuleManifest:
        if not isinstance(data, Mapping):
            raise TypeError('manifest JSON root must be an object')
        values = {name: _read(data, name) for name in ('schema_version', 'version', 'kind', 'module_name', 'menu_name', 'description', 'usage')}
        if isinstance(values['kind'], str):
            try:
                values['kind'] = ManifestKind(values['kind'])
            except ValueError:
                pass
        return cls(**values, commands=_parse_list(_read(data, 'commands'), CommandEntryModuleManifest))

    @classmethod
    def from_json(cls, path: str | Path) -> ModuleManifest:
        return cls.from_dict(ManifestsLoader.load_manifest(path))
