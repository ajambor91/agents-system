"""Load a manifest-selected application class for local execution."""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import keyword
import re
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

from lib.configuration import Configuration
from ..exceptions import ApiError


class ModuleLoader:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        self.instances: dict[tuple[str, str], object] = {}

    def load(self, section: dict[str, Any]) -> object:
        try:
            settings = type(self.configuration)
            path = re.sub(
                r"\$\{([A-Z][A-Z0-9_]*)\}",
                lambda match: str(getattr(settings, match[1])),
                section["absolute_module_path"],
            )
            directory = Path(path).expanduser().resolve(strict=True)
            metadata_text = (directory / "meta.json").read_text(encoding="utf-8")
            metadata = json.loads(metadata_text)
            module_name = metadata["application"]["module"]
            class_name = metadata["application"]["class"]
            identifiers = [*module_name.split("."), class_name]
            if any(not name.isidentifier() or keyword.iskeyword(name) for name in identifiers):
                raise ValueError("Invalid application module or class in meta.json")
            key = (str(directory), metadata_text)
            if key in self.instances:
                return self.instances[key]
            digest = hashlib.sha256((str(directory) + metadata_text).encode()).hexdigest()
            namespace = f"app_api_module_{digest}"
            if namespace not in sys.modules:
                package = ModuleType(namespace)
                package.__path__ = [str(directory)]
                package.__package__ = namespace
                package.__spec__ = ModuleSpec(namespace, loader=None, is_package=True)
                sys.modules[namespace] = package
            module = importlib.import_module(f"{namespace}.{module_name}")
            application_class = getattr(module, class_name)
            if not inspect.isclass(application_class):
                raise TypeError(f"{class_name} is not an application class")
            instance = application_class(self.configuration)
            self.instances[key] = instance
            return instance
        except Exception as exc:
            raise ApiError(
                f"Nie można załadować modułu {section['module_name']}: {exc}", exit_code=1
            ) from exc
