from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from manifests.app.consts import ENVIRONMENT_PATH_VARIABLES, ENVIRONMENT_FILENAME_VARIABLES
from manifests.app.exceptions.manifest_validation_error import _read
from manifests.app.models.manifest_abc import ManifestModel


@dataclass(slots=True, kw_only=True)
class EnvironmentVariableManifest(ManifestModel):
    name: str
    value: str
    description: str
    example: str

    def _validate_content(self) -> None:
        for name in ('name', 'value', 'description', 'example'):
            self._str(name, getattr(self, name))
        if isinstance(self.name, str):
            def check_name():
                if not re.fullmatch(r'[A-Z][A-Z0-9_]*', self.name):
                    raise ValueError('expected uppercase variable name')
            self._capture('name', check_name)
        if not isinstance(self.value, str):
            return
        def check_value():
            if any(character in self.value for character in ('\x00', '\r', '\n')):
                raise ValueError('control characters are forbidden')
            if '${' in self.value or re.search(r'\{\{[^{}]+\}\}', self.value.replace('{{agent_name}}', 'agent')):
                raise ValueError('configuration must be rendered; unresolved placeholder')
        self._capture('value', check_value)
        if isinstance(self.name, str) and self.name in ENVIRONMENT_PATH_VARIABLES:
            def check_path():
                path = Path(self.value)
                if not path.is_absolute() or '..' in path.parts:
                    raise ValueError(f'{self.name} must be a safe absolute path')
            self._capture('value', check_path)
        if isinstance(self.name, str) and self.name in ENVIRONMENT_FILENAME_VARIABLES:
            def check_filename():
                if self.value in {'.', '..'} or '/' in self.value or '\\' in self.value:
                    raise ValueError(f'{self.name} must be a filename')
            self._capture('value', check_filename)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EnvironmentVariableManifest:
        return cls(**{name: _read(data, name) for name in ('name', 'value', 'description', 'example')})
