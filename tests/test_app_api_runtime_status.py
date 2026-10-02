"""Runtime status shown in console menus."""
import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from app_api.app.models import ApiResult
from app_api.app.application import Application

console = importlib.import_module("app_api.app.console")


class RuntimeStatusTests(unittest.TestCase):
    def execute(self, arguments, available):
        class Configuration:
            APP_DIR = str(Path(__file__).resolve().parents[1])
            MODULES_MANIFEST_PATH = str(Path(APP_DIR) / "resources/agents-system.module.template.json")
        application = Application(Configuration())
        application.dispatcher = Mock(runtime_available=available)
        application.dispatcher.dispatch.return_value = "menu"
        with patch.object(application.catalog, "load", return_value={
            "menu_name": "menu", "description": "test", "sections": {"agents": {
                "module_name": "example", "section_name": "agents", "menu_name": "agents",
                "description": "test", "commands": [{"name": "list", "flags": []}],
            }},
        }), patch("app_api.app.services.renderer.Renderer.root_help", return_value=ApiResult(stdout="menu\n")):
            return application.run(arguments)

    def test_local_menu_has_red_warning_and_local_mode_line(self):
        with patch("sys.stdout.isatty", return_value=True), patch.dict("os.environ", {}, clear=True):
            output = self.execute([], False).stdout
        self.assertEqual(output, "\033[31mApplication runtime does not working\033[0m\nRunning in local mode\n\nmenu\n")

    def test_runtime_menu_has_green_status(self):
        with patch("sys.stdout.isatty", return_value=True), patch.dict("os.environ", {}, clear=True):
            self.assertEqual(self.execute([], True).stdout, "\033[32mApplication runtime and socket are OK\033[0m\n\nmenu\n")

    def test_machine_modes_and_command_results_have_no_banner(self):
        for arguments in (["--json"], ["--agent"], ["agents", "list"]):
            for available in (False, True):
                output = self.execute(arguments, available).stdout
                if arguments == ["agents", "list"]:
                    self.assertEqual(output, "menu\n")
                else:
                    self.assertNotIn("Application runtime", output)

    def test_raw_mode_has_no_ansi_codes(self):
        with patch("sys.stdout.isatty", return_value=True):
            output = self.execute(["--human-raw"], False).stdout
        self.assertNotIn("\033[", output)
        self.assertIn("Running in local mode", output)
