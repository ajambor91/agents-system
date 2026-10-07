"""UTF-8 JSON file and string reading, without domain validation."""
from __future__ import annotations

import logging

import json
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


class JsonLoader:
    @staticmethod
    def load(path: str | Path) -> Any:
        LOGGER.debug('Reading JSON document path=%s', path)
        with Path(path).open('r', encoding='utf-8') as stream:
            return json.load(stream)

    @staticmethod
    def loads(content: str | bytes | bytearray) -> Any:
        return json.loads(content)

    @staticmethod
    def getJsonFileContent(file_path: str | Path) -> Any:
        """Existing JSON API; callers can use load() when null is valid."""
        value = JsonLoader.load(file_path)
        if value is None:
            raise RuntimeError('Failed to load data from file')
        return value

    @staticmethod
    def save_file(content: dict[str, Any], path: str | Path) -> bool:
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return True