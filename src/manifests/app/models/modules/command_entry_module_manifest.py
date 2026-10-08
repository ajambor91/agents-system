from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from manifests.app.exceptions.manifest_validation_error import (
    _expected,
    _parse_list,
    _read,
)
from manifests.app.models.manifest_abc import ManifestModel
from manifests.app.models.modules.command_input_module_manifest import (
    CommandInputModuleManifest,
)
from manifests.app.models.modules.flag_entry_module_manifest import (
    FlagEntryModuleManifest,
)

@dataclass(slots=True, kw_only=True)
class CommandEntryModuleManifest(ManifestModel):
    name: str
    description: str
    usage: str
    implementation_status: str
    flags: list[FlagEntryModuleManifest]
    input: CommandInputModuleManifest | None = None

    def _validate_content(self) -> None:
        self._str("name", self.name)
        self._str("description", self.description)
        self._str("usage", self.usage)
        self._str("implementation_status", self.implementation_status)
        self._nested_list("flags", self.flags, FlagEntryModuleManifest)
        self._unique_names("flags", self.flags, FlagEntryModuleManifest)
        if self.input is not None:
            if isinstance(self.input, CommandInputModuleManifest):
                self._nested("input", self.input)
            else:
                self._capture("input", lambda: _expected(self.input, CommandInputModuleManifest))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CommandEntryModuleManifest:
        raw_input = data.get("input")
        if isinstance(raw_input, Mapping):
            raw_input = CommandInputModuleManifest.from_dict(raw_input)
        return cls(
            name=_read(data, "name"),
            description=_read(data, "description"),
            usage=_read(data, "usage"),
            implementation_status=_read(data, "implementation_status"),
            flags=_parse_list(_read(data, "flags"), FlagEntryModuleManifest),
            input=raw_input,
        )