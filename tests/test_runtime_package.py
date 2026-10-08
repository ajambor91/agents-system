"""Package imports and bootstrap delegation without starting a service."""

import importlib
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class RuntimePackageTests(unittest.TestCase):
    def test_each_module_imports_in_a_fresh_process(self):
        for path in (ROOT / "src/_runtime").rglob("*.py"):
            relative = path.relative_to(ROOT / "src").with_suffix("")
            parts = list(relative.parts)
            if parts[-1] == "__init__":
                parts.pop()
            module = ".".join(parts)
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", f"import {module}"],
                    cwd=ROOT / "src", capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_constructs_and_runs_runtime(self):
        entrypoint = importlib.import_module("_runtime.__main__")
        with patch.object(entrypoint, "get_env") as get_env, \
                patch.object(entrypoint, "RuntimeApp") as bootstrap, \
                patch.object(entrypoint, "MainRuntime") as runtime:
            self.assertEqual(entrypoint.main(), 0)
            get_env.assert_called_once_with()
            bootstrap.assert_called_once_with()
            data = bootstrap.return_value.get_data.return_value
            runtime.assert_called_once_with(data.instance_manager, data.configuration)
            runtime.return_value.run.assert_called_once_with()

    def test_only_python_module_entrypoint_exists(self):
        self.assertTrue((ROOT / 'src/_runtime/__main__.py').is_file())
        self.assertFalse((ROOT / 'src/_runtime' / ('main' + '.py')).exists())
