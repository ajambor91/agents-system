from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from manifests.app.exceptions.manifest_validation_error import (
    ManifestValidationError,
    _expected,
    _required_string,
)
from shared.exceptions.validation_issue import ValidationIssue

@dataclass(slots=True, kw_only=True)
class ManifestModel(ABC):
    """Common abstract root. Every model inherits the error list here."""

    errors: list[ValidationIssue] = field(default_factory=list, init=False, repr=False, compare=False)

    def validate(self) -> None:
        """Validate this object and all nested objects; never return False.

        On success: return None and leave errors empty.
        On failure: collect all available issues and raise one aggregate error.
        """
        self.errors.clear()
        for stage in (self._validate_common, self._validate_content):
            try:
                stage()
            except ManifestValidationError as exc:
                # Defensive fallback for a custom validator that raised
                # its own aggregate instead of calling _capture().
                self.errors.extend(exc.errors)
            except Exception as exc:
                # Capture unexpected validation errors and continue with
                # other stages rather than silently returning False.
                self.errors.append(ValidationIssue("<model>", exc))

        if self.errors:
            raise ManifestValidationError(type(self).__name__, self.errors)

    def _validate_common(self) -> None:
        """Hook for checks shared by a family of models."""

    @abstractmethod
    def _validate_content(self) -> None:
        """Check fields through _capture and nested objects through helpers."""

    def _capture(self, path: str, check: Callable[[], None]) -> None:
        try:
            check()
        except Exception as exc:
            self.errors.append(ValidationIssue(path, exc))

    def _str(self, name: str, value: Any) -> None:
        self._capture(name, lambda: _required_string(value))

    def _type(self, name: str, value: Any, expected_type: type) -> None:
        self._capture(name, lambda: _expected(value, expected_type))

    def _strings(self, name: str, value: Any) -> None:
        if type(value) is not list:
            self._type(name, value, list)
            return
        for index, item in enumerate(value):
            self._str(f"{name}[{index}]", item)

    def _nested_list(self, name: str, value: Any, model_type: type) -> None:
        if type(value) is not list:
            self._type(name, value, list)
            return
        for index, item in enumerate(value):
            path = f"{name}[{index}]"
            if not isinstance(item, model_type):
                self._capture(path, lambda obj=item: _expected(obj, model_type))
                continue
            self._nested(path, item)

    def _nested(self, path: str, item: ManifestModel) -> None:
        try:
            item.validate()
        except ManifestValidationError as exc:
            self.errors.extend(issue.with_prefix(path) for issue in exc.errors)
        except Exception as exc:
            self.errors.append(ValidationIssue(path, exc))

    def _unique_names(self, name: str, items: Any, model_type: type) -> None:
        if type(items) is not list:
            return  # the container type has already been reported
        seen: dict[str, int] = {}
        for index, item in enumerate(items):
            if not isinstance(item, model_type) or type(item.name) is not str:
                continue  # invalid items and names are reported by nested validation
            if item.name in seen:
                previous = seen[item.name]

                def duplicate(name=item.name, previous=previous) -> None:
                    raise ValueError(f"duplicate name {name!r}; first occurrence at index {previous}")

                self._capture(f"{name}[{index}].name", duplicate)
            else:
                seen[item.name] = index