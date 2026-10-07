"""Coordinate manifest I/O, model validation and reference resolution."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from lib.manifests_loader import ManifestsLoader
from .helpers import ManifestValidator
from .exceptions import ManifestStructureError


class ManifestsApp:
    def load_manifest(self, path: str | Path) -> Any:
        return ManifestsLoader.load_manifest(path)

    def parse_manifest(self, content: str | bytes | bytearray) -> Any:
        return ManifestsLoader.parse_manifest(content)

    def validate_manifest(self, manifest_data: Any) -> bool:
        return ManifestValidator.validate(manifest_data)

    def load_modules_manifest(self, path: str | Path) -> dict[str, Any]:
        return self.resolve_module_manifests(self.load_manifest(path))

    def resolve_module_manifests(self, data: dict[str, Any]) -> dict[str, Any]:
        self.validate_manifest(data)
        if data['kind'] != 'agents-system-modules-manifest':
            raise ManifestStructureError('Expected an agents-system-modules-manifest')
        resolved = copy.deepcopy(data)
        for child in resolved['children']:
            path = child.get('manifest_path')
            if path is None:
                continue
            detail = self.load_module_manifest(path, child['module_name'])
            for field in ('menu_name', 'description', 'usage', 'commands'):
                child[field] = detail[field]
            del child['manifest_path']
        return resolved

    def load_module_manifest(self, path: str | Path, module_name: str) -> dict[str, Any]:
        document = self.load_manifest(path)
        self.validate_manifest(document)
        if document['kind'] != 'module-manifest':
            raise ManifestStructureError(f'{path}: expected module-manifest')
        if document['module_name'] != module_name:
            raise ManifestStructureError(f'{path}: module_name does not match {module_name!r}')
        return document

    def load_module_metadata(self, module_dir: str | Path) -> Any:
        return ManifestsLoader.load_module_metadata(module_dir)

    def load_directory(self, directory: str | Path) -> dict[Path, Any]:
        return ManifestsLoader.load_directory(directory)
