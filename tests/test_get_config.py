"""Selection rules for the shared Configuration factory."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

module = importlib.import_module("shared.get_config")


class GetConfigTests(unittest.TestCase):
    def _load(
        self,
        *,
        dev_config: bool | None,
        path: Path | None = None,
        installed_exists: bool = True,
    ) -> Path:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            development = root / "resources" / "app_env.json"
            installed = root / "etc" / "app_env.json"
            development.parent.mkdir()
            installed.parent.mkdir()
            development.write_text("{}")
            if installed_exists:
                installed.write_text("{}")
            explicit = path or root / "explicit.json"
            if path is None:
                explicit.write_text("{}")

            selected: list[Path] = []

            def load(source):
                selected.append(Path(source))
                return {"variables": [{"name": "VALUE", "value": "ok"}]}

            with (
                patch.object(module, "DEV_CONFIG_PATH", development),
                patch.object(module, "APP_CONFIG_PATH", installed),
                patch.object(module.JsonLoader, "getJsonFileContent", side_effect=load),
                patch.object(module, "Configuration", side_effect=lambda values: values),
            ):
                module.get_config(dev_config, explicit if path is not None else None)

            return selected[0]

    def test_development_mode_uses_local_resource_by_default(self) -> None:
        selected = self._load(dev_config=True)
        self.assertEqual(selected.name, "app_env.json")
        self.assertEqual(selected.parent.name, "resources")

    def test_development_mode_honors_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            explicit = Path(directory) / "custom.json"
            explicit.write_text("{}")
            selected = self._load(dev_config=True, path=explicit)
        self.assertEqual(selected, explicit.resolve())

    def test_system_mode_always_uses_hardcoded_install_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ignored = Path(directory) / "ignored.json"
            ignored.write_text("{}")
            selected = self._load(dev_config=False, path=ignored)
        self.assertNotEqual(selected, ignored.resolve())
        self.assertEqual(selected.parent.name, "etc")

    def test_automatic_mode_falls_back_to_development_resource(self) -> None:
        selected = self._load(dev_config=None, installed_exists=False)
        self.assertEqual(selected.parent.name, "resources")


if __name__ == "__main__":
    unittest.main()
