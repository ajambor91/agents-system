"""Manifest I/O only; callers own schema and domain validation."""
from __future__ import annotations

import logging

import json
from pathlib import Path
from typing import Any

from lib.json_loader import JsonLoader
from .exceptions import ManifestJsonError, ManifestReadError


LOGGER = logging.getLogger(__name__)


class ManifestsLoader:
    @staticmethod
    def load_manifest(path: str | Path) -> Any:
        LOGGER.debug('Reading manifest path=%s', path)
        try:
            return JsonLoader.load(path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f'Brak manifestu: {path}') from exc
        except OSError as exc:
            raise ManifestReadError(f'Nie można odczytać manifestu {path}: {exc}') from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ManifestJsonError(f'Nieprawidłowy JSON manifestu {path}: {exc}') from exc

    @staticmethod
    def parse_manifest(content: str | bytes | bytearray) -> Any:
        try:
            return JsonLoader.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ManifestJsonError(f'Nieprawidłowy JSON manifestu: {exc}') from exc

    @staticmethod
    def load_module_metadata(module_dir: str | Path) -> Any:
        LOGGER.debug('Reading module metadata module_dir=%s', module_dir)
        return ManifestsLoader.load_manifest(Path(module_dir) / 'meta.json')

    @staticmethod
    def load_directory(directory: str | Path) -> dict[Path, Any]:
        LOGGER.debug('Discovering manifests in directory directory=%s', directory)
        return {
            path: ManifestsLoader.load_manifest(path)
            for path in sorted(Path(directory).glob('*.json'))
            if path.is_file()
        }
