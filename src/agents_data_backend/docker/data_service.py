from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from lib.configuration import Configuration
from lib.json_loader import JsonLoader


class DataService:


    def _validate_path(path: str | Path) -> Path:
        target = Path(path).absolute()
        if target.is_symlink():
            raise ValueError(f"JSON path must not be a symlink: {target}")
        if target.exists() and not target.is_file():
            raise ValueError(f"JSON path must be a regular file: {target}")
        return target

    def save_json_data(
        self, data: dict[str, Any], path: str | Path, *, overwrite: bool = False
    ) -> bool:
        """Atomically save an object; replacing an existing file is opt-in."""
        target = self._validate_path(path)
        if not isinstance(data, dict):
            raise TypeError("JSON data must be an object")
        if target.exists() and not overwrite:
            raise FileExistsError(target)
        content = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=f".{target.name}.", suffix=".tmp", delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if overwrite:
                self._validate_path(target)
                os.replace(temporary, target)
            else:
                # Publish without replacing a file created by another writer.
                os.link(temporary, target)
            return True
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def get_json(self, path: str | Path) -> dict[str, Any]:
        """Read an object; missing files and invalid JSON raise errors."""
        target = self._validate_path(path)
        content = JsonLoader.load(target)
        if not isinstance(content, dict):
            raise TypeError(f"JSON data must be an object: {target}")
        return content

    def update_json(
        self, data: dict[str, Any], path: str | Path, nested: bool = False
    ) -> bool:
        """Update an existing object; nested=True recursively merges dictionaries.

        Lists and scalar values are replaced. Missing files raise FileNotFoundError.
        """
        if not isinstance(data, dict):
            raise TypeError("JSON update must be an object")
        existing = self.get_json(path)

        def merge(target: dict[str, Any], changes: dict[str, Any]) -> None:
            for key, value in changes.items():
                if nested and isinstance(target.get(key), dict) and isinstance(value, dict):
                    merge(target[key], value)
                else:
                    target[key] = deepcopy(value)

        merge(existing, data)
        return self.save_json_data(existing, path, overwrite=True)
