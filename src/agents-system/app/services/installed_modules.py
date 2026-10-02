"""Read installed module records from local installation documents."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.configuration import Configuration
from shared.json_loader import JsonLoader
from ..exceptions import ConfigurationError


class InstalledModulesReader:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

    def list_modules(self) -> list[dict[str, Any]]:
        directory = Path(type(self.configuration).INSTALLED_MODULES_DIR).expanduser()
        if not directory.is_absolute():
            raise ConfigurationError("INSTALLED_MODULES_DIR musi być ścieżką absolutną")
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise ConfigurationError(f"INSTALLED_MODULES_DIR nie jest katalogiem: {directory}")
        records: dict[str, dict[str, Any]] = {}
        try:
            for path in sorted(directory.glob("*.json")):
                if not path.is_file():
                    continue
                document = JsonLoader.getJsonFileContent(path)
                modules = document.get("modules") if isinstance(document, dict) else None
                if not isinstance(modules, list):
                    raise ConfigurationError(f"{path}: modules musi być tablicą")
                for module in modules:
                    if not isinstance(module, dict) or not isinstance(module.get("name"), str) or not module["name"]:
                        raise ConfigurationError(f"{path}: moduł wymaga niepustego name")
                    name = module["name"]
                    if name in records and records[name] != module:
                        raise ConfigurationError(f"{path}: sprzeczne wpisy modułu {name}")
                    records[name] = module
        except ConfigurationError:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            raise ConfigurationError(f"Nie można odczytać zainstalowanych modułów: {exc}") from exc
        return list(records.values())
