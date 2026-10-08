from __future__ import annotations

from typing import Any, Mapping

from shared.exceptions.missing import _MISSING
from shared.exceptions.validation_issue import ValidationIssue


class ManifestValidationError(ValueError):
    """Aggregate exception; .errors contains every captured ValidationIssue."""

    def __init__(self, model: str, errors: list[ValidationIssue]) -> None:
        self.model = model
        self.errors = list(errors)
        details = "\n".join(f"  {index}. {item}" for index, item in enumerate(self.errors, 1))
        super().__init__(f"{model} validation failed ({len(self.errors)} errors):\n{details}")


def _read(data: Mapping[str, Any], key: str) -> Any:
    return data.get(key, _MISSING)


def _parse_list(raw: Any, model: type) -> Any:
    """Convert valid dict elements, preserve bad input for later validation."""
    if type(raw) is not list:
        return raw
    return [model.from_dict(item) if isinstance(item, Mapping) else item for item in raw]


def _expected(value: Any, expected_type: type) -> None:
    if value is _MISSING:
        raise ValueError("required field is missing")
    # Strict types: bool must never be accepted as int.
    if type(value) is not expected_type:
        raise TypeError(f"expected {expected_type.__name__}, got {type(value).__name__}")


def _required_string(value: Any) -> None:
    _expected(value, str)
    if not value.strip():
        raise ValueError("string must not be empty")


def _optional_string(value: Any) -> None:
    if value is not None:
        _required_string(value)
