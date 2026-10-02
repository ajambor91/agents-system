"""Packaging and path-based runtime loading contracts for app_api."""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
APP_API_ROOT = SOURCE_ROOT / "app_api"
sys.path.insert(0, str(SOURCE_ROOT))

from _runtime.app.class_builder import ClassBuilder  # noqa: E402
from _runtime.app.models.meta_data_class import MetaDataClass  # noqa: E402
from _runtime.app.models.module_entry import ModuleEntry  # noqa: E402


class AppApiPackagingTests(unittest.TestCase):
    def test_app_api_remains_loadable_from_its_directory(self) -> None:
        namespace = "app_api_packaging_test"
        entry = ModuleEntry(
            absolute_module_path=str(APP_API_ROOT),
            is_runtime=True,
            meta_data=MetaDataClass(
                namespace=namespace,
                entrypoint="__main__.py",
                module="app.application",
                class_name="Application",
            ),
            runtime=["main"],
            module_name="app_api",
        )

        application_class = ClassBuilder(None)._load_class(entry)

        self.assertEqual(application_class.__name__, "Application")
        self.assertEqual(
            application_class.__module__,
            f"runtime_plugin_{namespace}.app.application",
        )

    def test_distribution_declares_local_socket_library(self) -> None:
        configuration = tomllib.loads(
            (APP_API_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(configuration["project"]["name"], "agents-system-app-api")
        self.assertIn(
            "unix-socket-client==0.1.0",
            configuration["project"]["dependencies"],
        )
        self.assertEqual(
            configuration["tool"]["setuptools"]["package-dir"]["app_api"],
            ".",
        )


if __name__ == "__main__":
    unittest.main()

