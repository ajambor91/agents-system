from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from manifests.app.consts import ENVIRONMENT_SCHEMA_VERSION, ENVIRONMENT_REQUIRED_VARIABLES
from manifests.app.enums.manifest_kinds import ManifestKind
from manifests.app.exceptions.manifest_validation_error import _read, _parse_list
from manifests.app.models.manifest_abc import ManifestModel
from .variable import EnvironmentVariableManifest


@dataclass(slots=True, kw_only=True)
class EnvironmentManifest(ManifestModel):
    schema_version: int
    kind: ManifestKind
    variables: list[EnvironmentVariableManifest]

    def _validate_common(self) -> None:
        self._type('schema_version', self.schema_version, int)
        def check_schema():
            if self.schema_version != ENVIRONMENT_SCHEMA_VERSION:
                raise ValueError('expected schema_version=1')
        self._capture('schema_version', check_schema)
        self._type('kind', self.kind, ManifestKind)
        def check_kind():
            if self.kind != ManifestKind.ENVIRONMENT:
                raise ValueError('expected agents-system-environment')
        self._capture('kind', check_kind)

    def _validate_content(self) -> None:
        self._nested_list('variables', self.variables, EnvironmentVariableManifest)
        self._unique_names('variables', self.variables, EnvironmentVariableManifest)
        values = {}
        if isinstance(self.variables, list):
            values = {item.name: item.value for item in self.variables
                      if isinstance(item, EnvironmentVariableManifest)
                      and isinstance(item.name, str) and isinstance(item.value, str)}
        for name in sorted(ENVIRONMENT_REQUIRED_VARIABLES - values.keys()):
            def missing(name=name):
                raise ValueError(f'required variable is missing: {name}')
            self._capture('variables.' + name, missing)
        for name, choices in {'INSTALL_MODE': {'system', 'dev'}, 'BASH_SOURCE': {'true', 'false'}}.items():
            if name in values:
                def check_choice(name=name, choices=choices):
                    if values[name] not in choices:
                        raise ValueError(f'expected one of {sorted(choices)}')
                self._capture('variables.' + name, check_choice)
        for name in ('APP_NAME', 'MAIN_APP_NAME', 'USER_SYSTEM', 'USER_GROUP'):
            if name in values:
                def check_identifier(name=name):
                    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', values[name]):
                        raise ValueError('invalid identifier')
                self._capture('variables.' + name, check_identifier)
        for name in ('MAX_MESSAGE_BYTES_BASE', 'MAX_MESSAGE_BYTES_MULTIPLIER'):
            if name in values:
                def check_integer(name=name):
                    value = values[name]
                    if not value.isascii() or not value.isdigit() or int(value) <= 0:
                        raise ValueError('expected positive integer string')
                self._capture('variables.' + name, check_integer)
        relationships = {
            'APP_DIR': ('INSTALL_DIR', ''), 'MODULES_DIR': ('APP_DIR', 'src'),
            'APP_ENV_PATH': ('APP_CONFIG_DIR', values.get('APP_ENV_FILE', 'app_env.json')),
            'MODULES_MANIFEST_PATH': ('APP_CONFIG_DIR', values.get('MODULES_MANIFEST_FILE', 'agents-system.module.json')),
            'APP_RUNTIME_PATH': ('APP_RUNTIME_DIR', values.get('APP_RUNTIME', '')),
            'AGENTS_DATA_RUNTIME_PATH': ('APP_RUNTIME_DIR', values.get('AGENTS_DATA_RUNTIME', '')),
        }
        for name, (parent, suffix) in relationships.items():
            if name in values and parent in values:
                def check_relationship(name=name, parent=parent, suffix=suffix):
                    if Path(values[name]) != Path(values[parent]) / suffix:
                        raise ValueError(f'must match {parent}/{suffix}')
                self._capture('variables.' + name, check_relationship)
        for name in ('APP_DIR', 'APP_CONFIG_DIR', 'APP_DATA_DIR', 'APP_RUNTIME_DIR'):
            if name in values:
                def check_root(name=name):
                    if Path(values[name]) == Path('/'):
                        raise ValueError('filesystem root cannot be an application directory')
                self._capture('variables.' + name, check_root)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EnvironmentManifest:
        raw_kind = _read(data, 'kind')
        if isinstance(raw_kind, str):
            try:
                raw_kind = ManifestKind(raw_kind)
            except ValueError:
                pass
        return cls(schema_version=_read(data, 'schema_version'), kind=raw_kind,
                   variables=_parse_list(_read(data, 'variables'), EnvironmentVariableManifest))
