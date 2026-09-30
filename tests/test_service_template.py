"""Contract tests for the shared runtime systemd unit template."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "resources" / "agents_manager.template.service"


class ServiceTemplateTests(unittest.TestCase):
    def test_template_runs_only_the_shared_runtime(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        exec_start = [line for line in content.splitlines() if line.startswith("ExecStart=")]
        self.assertEqual(exec_start, ["ExecStart={{PYTHON_BIN}} -u {{APP_DIR}}/src/runtime/main.py"])
        self.assertNotIn("src/app_api/main.py", content)
        self.assertNotIn("src/agents-manager/main.py", content)
        self.assertNotIn("src/agents-system/main.py", content)

    def test_template_declares_identity_paths_and_future_apps_manifest(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")
        required = {
            "INSTALL_MODE",
            "APP_NAME",
            "USER_SYSTEM",
            "USER_GROUP",
            "USER_SYSTEM_HOME",
            "APP_DIR",
            "APP_CONFIG_DIR",
            "APP_DATA_DIR",
            "APP_RUNTIME_DIR",
            "APP_RUNTIME_PATH",
            "APP_ENV_PATH",
            "MODULES_MANIFEST_PATH",
            "PYTHON_BIN",
        }
        placeholders = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", content))

        self.assertEqual(placeholders, required)
        self.assertIn('Environment="MODULES_MANIFEST_PATH={{MODULES_MANIFEST_PATH}}"', content)
        self.assertNotIn("ConditionPathExists={{MODULES_MANIFEST_PATH}}", content)
        self.assertIn("Restart=on-failure", content)


if __name__ == "__main__":
    unittest.main()
