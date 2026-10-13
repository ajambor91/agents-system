"""Shared conversion to independent, plain Python containers."""
from copy import deepcopy
from dataclasses import fields
from typing import Any, TypeVar

_T = TypeVar("_T")


def _plain(value: Any) -> Any:
    if isinstance(value, (_MappingModel, _MappingCollection, _SequenceCollection)):
        return value.to_mapping()
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return deepcopy(value)


class _MappingModel:
    __slots__ = ()

    def to_mapping(self) -> dict[str, Any]:
        """Convert fields recursively, flatten extra and omit None fields."""
        result = _plain(getattr(self, "extra", {}))
        for item in fields(self):
            if item.name == "extra":
                continue
            value = getattr(self, item.name)
            if value is not None:
                result[item.name] = _plain(value)
        return result


class _MappingCollection(dict[str, _T]):
    def to_mapping(self) -> dict[str, Any]:
        return {key: _plain(value) for key, value in self.items()}


class _SequenceCollection(list[_T]):
    def to_mapping(self) -> list[Any]:
        """List-shaped collections retain their order and list shape."""
        return [_plain(value) for value in self]
