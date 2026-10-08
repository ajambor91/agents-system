from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from manifests.app.exceptions.manifest_validation_error import (
    _expected,
    _optional_string,
    _read,
)
from manifests.app.models.manifest_abc import ManifestModel

@dataclass(slots=True, kw_only=True)
class FlagEntryModuleManifest(ManifestModel):
    name: str
    short: str | None
    long: str
    aliases: list[str]
    description: str
    usage: str
    takes_value: bool
    type: str
    required: bool
    default: str | int | float | bool | None = None

    def _validate_content(self) -> None:
        self._str("name", self.name)
        self._capture("short", lambda: _optional_string(self.short))
        self._str("long", self.long)
        self._strings("aliases", self.aliases)
        self._str("description", self.description)
        self._str("usage", self.usage)
        self._type("takes_value", self.takes_value, bool)
        self._str("type", self.type)
        self._type("required", self.required, bool)

        def check_default() -> None:
            if self.default is not None and type(self.default) not in (str, int, float, bool):
                raise TypeError("default must be a JSON scalar or null")
            default_types = {"boolean": bool, "integer": int, "string": str}
            expected_type = default_types.get(self.type) if type(self.type) is str else None
            if expected_type is not None and self.default is not None:
                _expected(self.default, expected_type)

        self._capture("default", check_default)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FlagEntryModuleManifest:
        return cls(
            name=_read(data, "name"),
            short=_read(data, "short"),
            long=_read(data, "long"),
            aliases=_read(data, "aliases"),
            description=_read(data, "description"),
            usage=_read(data, "usage"),
            takes_value=_read(data, "takes_value"),
            type=_read(data, "type"),
            required=_read(data, "required"),
            default=data.get("default"),
        )