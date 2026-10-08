"""New application Configuration contract tests."""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from _runtime.app.class_builder import ClassBuilder  # noqa: E402
from _runtime.app.models.meta_data_class import MetaDataClass  # noqa: E402
from _runtime.app.models.module_entry import ModuleEntry  # noqa: E402


class ConfigurationContractTests(unittest.TestCase):
    def load_application_class(self, app: str, namespace: str):
        metadata = __import__("json").loads(
            (SOURCE_ROOT / app / "meta.json").read_text(encoding="utf-8")
        )
        entry = ModuleEntry(
            absolute_module_path=str(SOURCE_ROOT / app),
            is_runtime=False,
            meta_data=MetaDataClass(
                namespace=namespace,
                entrypoint=metadata["entrypoint"],
                module=metadata["application"]["module"],
                class_name=metadata["application"]["class"],
            ),
            runtime=["main"],
            module_name=app,
        )
        return ClassBuilder(None)._load_class(entry)

    def test_main_classes_accept_only_configuration(self) -> None:
        for index, app in enumerate(("agents_system_cli", "agents_system", "agents_manager")):
            with self.subTest(app=app):
                application_class = self.load_application_class(
                    app,
                    f"configuration_contract_{index}",
                )
                parameters = list(
                    inspect.signature(application_class.__init__).parameters
                )
                self.assertEqual(parameters, ["self", "configuration"])

    def test_obsolete_configuration_services_are_removed(self) -> None:
        self.assertFalse(
            (SOURCE_ROOT / "agents_system_cli" / "app" / "services" / "runtime.py").exists()
        )
        for name in ("environment.py", "installation.py", "status.py", "system.py"):
            self.assertFalse(
                (SOURCE_ROOT / "agents_system" / "app" / "services" / name).exists()
            )


if __name__ == "__main__":
    unittest.main()
