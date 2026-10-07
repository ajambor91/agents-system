"""Dynamic application construction tests for the shared _runtime."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from _runtime.app.class_builder import ClassBuilder  # noqa: E402
from _runtime.app.class_loader import ClassLoader  # noqa: E402


class TestConfiguration:
    APP_DIR = str(ROOT)
    MODULES_MANIFEST_PATH = str(
        ROOT / "resources" / "agents-system.module.template.json"
    )
    USER_SYSTEM = "user-system"
    APP_DATA_DIR = str(ROOT / ".test-data")


class RuntimeTests(unittest.TestCase):
    def test_runtime_injects_one_configuration_into_meta_applications(self) -> None:
        manifest = json.loads(
            (ROOT / "resources" / "agents-system.module.template.json").read_text(
                encoding="utf-8"
            )
        )
        for child in manifest["children"]:
            child["absolute_module_path"] = child["absolute_module_path"].replace(
                "${MODULES_DIR}",
                str(SOURCE_ROOT),
            )

        configuration = TestConfiguration()
        loader = ClassLoader(manifest)
        self.assertEqual(
            set(loader.getClasses()),
            {"agents_system_cli", "agents_system", "agents_manager"},
        )

        instances = ClassBuilder(loader, configuration).build_class_tree()
        self.assertEqual(set(instances), set(loader.getClasses()))
        self.assertIs(instances["agents_system_cli"].instance_object.configuration, configuration)
        self.assertIs(
            instances["agents_system"].instance_object.configuration,
            configuration,
        )
        self.assertIs(
            instances["agents_manager"].instance_object._configuration,
            configuration,
        )


if __name__ == "__main__":
    unittest.main()
