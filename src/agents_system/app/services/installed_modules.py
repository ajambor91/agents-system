"""Read and check installed module records through the manifests application."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from lib.configuration import Configuration
from manifests import ManifestsApp
from shared.models.modules_list_data import ModuleData, ModulesListData
from ..exceptions import ConfigurationError


LOGGER = logging.getLogger(__name__)


class InstalledModulesReader:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

    def list_modules(self) -> ModulesListData:
        LOGGER.debug('Starting installed_modules.list_modules')
        directory = Path(type(self.configuration).INSTALLED_MODULES_DIR).expanduser()
        if not directory.is_absolute() or '..' in directory.parts:
            raise ConfigurationError('INSTALLED_MODULES_DIR musi być bezpieczną ścieżką absolutną')
        if not directory.exists():
            return ModulesListData()
        if not directory.is_dir():
            raise ConfigurationError(f'INSTALLED_MODULES_DIR nie jest katalogiem: {directory}')
        records: dict[str, dict[str, Any]] = {}
        try:
            for path, document in ManifestsApp().load_directory(directory).items():
                modules = document.get('modules') if isinstance(document, dict) else None
                if not isinstance(modules, list):
                    raise ConfigurationError(f'{path}: modules musi być tablicą')
                for module in modules:
                    if not isinstance(module, dict) or not isinstance(module.get('name'), str) or not module['name']:
                        raise ConfigurationError(f'{path}: moduł wymaga niepustego name')
                    name = module['name']
                    if name in records and records[name] != module:
                        raise ConfigurationError(f'{path}: sprzeczne wpisy modułu {name}')
                    records[name] = module
        except ConfigurationError:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            raise ConfigurationError(f'Nie można odczytać zainstalowanych modułów: {exc}') from exc
        return ModulesListData(modules={
            name: ModuleData(
                module_name=name,
                description=record.get('description', '')
                if isinstance(record.get('description', ''), str) else '',
            )
            for name, record in records.items()
        })
