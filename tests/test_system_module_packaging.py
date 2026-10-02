"""Module architecture, public API and thin entrypoint contracts."""
from __future__ import annotations

import importlib
import inspect
import json
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

package = importlib.import_module("agents-system")
entrypoint = importlib.import_module("agents-system.__main__")
console_module = importlib.import_module("agents-system.app.console")


class SystemModulePackagingTests(unittest.TestCase):
    def configuration(self):
        class Configuration:
            APP_DIR = str(ROOT)
            MODULES_MANIFEST_PATH = str(ROOT / "resources/agents-system.module.template.json")
            INSTALLED_MODULES_DIR = "/tmp/agents-system-packaging-test-nonexistent"
        return Configuration()

    def test_application_accepts_configuration_and_exposes_only_modules(self):
        self.assertEqual(list(inspect.signature(package.Application.__init__).parameters), ["self", "configuration"])
        public = [name for name, method in inspect.getmembers(package.Application, inspect.isfunction) if not name.startswith("_")]
        self.assertEqual(public, ["modules"])

    def test_entrypoint_delegates_to_console(self):
        self.assertEqual(entrypoint.execute, console_module.Console.execute)
        self.assertEqual(entrypoint.emit, console_module.Console.emit)
        self.assertEqual(entrypoint.main, console_module.Console.main)
        configuration = self.configuration()
        with patch.object(console_module, "get_config", return_value=configuration) as get_config:
            result = entrypoint.execute(["--json", "modules", "--installed"])
        get_config.assert_called_once_with()
        self.assertEqual(result.data["mode"], "installed")

    def test_retired_architecture_files_are_removed(self):
        source = ROOT / "src/agents-system/app"
        for path in ("command.py", "errors.py", "commands", "specs", "services/users.py", "models/command_request.py", "models/command_result.py"):
            self.assertFalse((source / path).exists(), path)

    def test_template_lists_only_the_public_modules_method(self):
        document = json.loads((ROOT / "resources/agents-system.module.template.json").read_text())
        system = next(child for child in document["children"] if child["module_name"] == "agents-system")
        self.assertEqual([command["name"] for command in system["commands"]], ["modules"])
        self.assertTrue(hasattr(package.Application, system["commands"][0]["method"]))

    def test_package_layout_keeps_the_fixed_source_directory(self):
        configuration = tomllib.loads((ROOT / "src/agents-system/pyproject.toml").read_text())
        self.assertEqual(configuration["tool"]["setuptools"]["package-dir"]["agents_system"], ".")
        self.assertIn("agents_system.app.models", configuration["tool"]["setuptools"]["packages"])
        self.assertIn("agents_system.app.exceptions", configuration["tool"]["setuptools"]["packages"])
        self.assertFalse((ROOT / "src/agents_system").exists())

    def test_public_wrapper_menu_matches_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        commands = [path.stem.replace("-", "_") for path in (ROOT / "host_scripts").glob("*.sh")]
        self.assertEqual(sorted(manifest["commands"]), sorted(commands))
        self.assertEqual(commands, ["asystem"])
