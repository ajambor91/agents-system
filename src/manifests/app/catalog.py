"""Build a console menu from resolved module manifests in memory."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .manifests_app import ManifestsApp
from .exceptions import ManifestStructureError


class ManifestCatalog:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)

    def load(self) -> dict[str, Any]:
        source = ManifestsApp().load_modules_manifest(self.manifest_path)
        sections: dict[str, Any] = {}
        for child in source['children']:
            if not child['is_menu_option']:
                continue
            name = child['section_name']
            if name in sections:
                raise ManifestStructureError(f'Powtórzona sekcja menu: {name}')
            sections[name] = {
                'schema_version': source['schema_version'],
                'version': source['version'],
                'kind': 'asystem-menu-manifest',
                'absolute_path': str(self.manifest_path),
                'module_name': child['module_name'],
                'absolute_module_path': child['absolute_module_path'],
                'section_name': name,
                'menu_name': child['menu_name'],
                'description': child['description'],
                'commands': copy.deepcopy(child['commands']),
            }
        if not sections:
            raise ManifestStructureError(f'Brak modułów menu w {self.manifest_path}')
        return {
            'schema_version': source['schema_version'],
            'version': source['version'],
            'kind': 'asystem-app-manifest',
            'app_name': 'agents_system_cli',
            'absolute_path': str(self.manifest_path),
            'menu_name': 'Agents System',
            'description': 'Konsola zarządzania systemem i agentami.',
            'sections': sections,
        }
