"""Public factory for catalog dictionaries, JSON documents and UTF-8 files."""

from pathlib import Path
from typing import Any

from manifests import ManifestsApp
from .models.modules_catalog import ModulesCatalog
from .factories.modules_factory import ModulesCatalogFactory


class ModulesFactory:
    """Construct catalogs without maintaining global state."""

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated")

    @staticmethod
    def create_modules_from_json(json_data: str | bytes) -> ModulesCatalog:
        return ModulesFactory.create_modules_from_dict(ManifestsApp().parse_manifest(json_data))

    @staticmethod
    def create_modules_from_json_file(json_file_path: str | Path) -> ModulesCatalog:
        return ModulesFactory.create_modules_from_dict(ManifestsApp().load_manifest(json_file_path))

    @staticmethod
    def create_modules_from_dict(dict_data: dict[str, Any]) -> ModulesCatalog:
        if dict_data.get('kind') == 'agents-system-modules-manifest':
            dict_data = ManifestsApp().resolve_module_manifests(dict_data)
        return ModulesCatalogFactory.from_dict(dict_data)
