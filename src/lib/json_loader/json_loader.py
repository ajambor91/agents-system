"""UTF-8 JSON file and string reading, without domain validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonLoader:
    @staticmethod
    def load(path: str | Path) -> Any:
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
