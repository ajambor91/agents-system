"""Packaging and path-based runtime loading contracts for agents_system_cli."""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
AGENTS_SYSTEM_CLI_ROOT = SOURCE_ROOT / "agents_system_cli"
sys.path.insert(0, str(SOURCE_ROOT))

from _runtime.app.class_builder import ClassBuilder  # noqa: E402
from _runtime.app.models.meta_data_class import MetaDataClass  # noqa: E402
from _runtime.app.models.module_entry import ModuleEntry  # noqa: E402


class AgentsSystemCLIPackagingTests(unittest.TestCase):
    def test_agents_system_cli_remains_loadable_from_its_directory(self) -> None:
        namespace = "agents_system_cli_packaging_test"
        entry = ModuleEntry(
            absolute_module_path=str(AGENTS_SYSTEM_CLI_ROOT),
            is_runtime=True,
            meta_data=MetaDataClass(
                namespace=namespace,
                entrypoint="__main__.py",
                module="app.application",
                class_name="AgentsSystemCLI",
            ),
            runtime=["main"],
            module_name="agents_system_cli",
        )

        application_class = ClassBuilder(None)._load_class(entry)

        self.assertEqual(application_class.__name__, "AgentsSystemCLI")
        self.assertEqual(
            application_class.__module__,
            f"runtime_plugin_{namespace}.app.application",
        )

    def test_distribution_declares_local_socket_library(self) -> None:
        configuration = tomllib.loads(
            (AGENTS_SYSTEM_CLI_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(configuration["project"]["name"], "agents_system_cli")
        self.assertIn(
            "unix-socket-client==0.1.0",
            configuration["project"]["dependencies"],
        )
        self.assertEqual(
            configuration["tool"]["setuptools"]["package-dir"]["agents_system_cli"],
            ".",
        )


if __name__ == "__main__":
    unittest.main()

