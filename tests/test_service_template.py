"""Contract tests for the shared runtime systemd unit template."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "resources" / "system.template.service"


class ServiceTemplateTests(unittest.TestCase):
    def test_manager_template_renders_to_valid_root_service(self) -> None:
        content = (ROOT / 'resources/manager.template.service').read_text()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            values = {
                'APP_DIR': str(ROOT), 'APP_NAME': 'agents-system-manager',
                'INSTALL_MODE': 'system', 'USER_SYSTEM': 'root',
                'USER_SYSTEM_HOME': '/root', 'PYTHON_BIN': sys.executable,
                'APP_CONFIG_DIR': str(base), 'APP_DATA_DIR': str(base),
                'APP_RUNTIME_DIR': str(base), 'APP_ENV_PATH': str(base / 'app_env.json'),
                'MODULES_MANIFEST_PATH': str(base / 'modules.json'),
                'SYSTEM_AGENT_MANAGER_RUNTIME_SOCKET': str(base / 'manager.sock'),
                'SYSTEM_AGENT_MANAGER_RUNTIME_PID': str(base / 'manager.pid'),
            }
            for name, value in values.items():
                content = content.replace('{{' + name + '}}', value)
            self.assertNotIn('{{', content)
            self.assertIn('User=root\nGroup=root\n', content)
            self.assertIn('ExecStart=' + sys.executable + ' -u -m agents_manager_runtime', content)
            unit = base / 'agents-system-manager.service'
            unit.write_text(content)
            result = subprocess.run(['systemd-analyze', 'verify', str(unit)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_template_runs_only_the_shared_runtime(self) -> None:
        content = TEMPLATE.read_text(encoding="utf-8")

        exec_start = [line for line in content.splitlines() if line.startswith("ExecStart=")]
        self.assertEqual(exec_start, ["ExecStart={{PYTHON_BIN}} -u {{APP_DIR}}/src/_runtime/__main__.py"])
        self.assertNotIn("src/agents_system_cli/__main__.py", content)
        self.assertNotIn("src/agents_manager/__main__.py", content)
        self.assertNotIn("src/agents_system/__main__.py", content)

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
