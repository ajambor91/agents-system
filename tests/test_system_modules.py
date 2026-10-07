"""Installed modules, resident instance API and the public system command."""
from __future__ import annotations

import importlib
import json
import socket
import threading
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src/lib"))

from agents_system_cli.app.application import AgentsSystemCLI as ConsoleApplication
from agents_system_cli.app.services.module_loader import ModuleLoader
from agents_system_cli.app.services.flag_parser import FlagParser
from _runtime.app.instance_manager import InstanceManager
from _runtime.app.instance_manager_wrapper import InstanceManagerWrapper
from internal_scripts.render_modules_manifest import render
from shared.socket_client import RuntimeUnavailableError
from shared.socket_client import RuntimeCallError


class SystemModulesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        installed = self.base / "installed"
        installed.mkdir()
        class Configuration:
            APP_DIR = str(ROOT)
            MODULES_DIR = str(ROOT / "src")
            MODULES_MANIFEST_PATH = str(ROOT / "resources/agents-system.module.template.json")
            INSTALLED_MODULES_DIR = str(installed)
            SYSTEM_AGENT_RUNTIME_SOCKET = str(self.base / "missing.sock")
            MAX_MESSAGE_BYTES_BASE = "1024"
            MAX_MESSAGE_BYTES_MULTIPLIER = "1024"
            USER_SYSTEM = "test-user"
        self.configuration = Configuration()
        self.installed = installed
        section = {"module_name": "agents_system", "absolute_module_path": str(ROOT / "src/agents_system")}
        self.application = ModuleLoader(self.configuration).load(section)
        self.errors = importlib.import_module(self.application.__class__.__module__.rsplit(".", 1)[0] + ".exceptions")
        self.runtime_module = importlib.import_module(self.application.__class__.__module__.rsplit(".", 1)[0] + ".services.runtime_modules")

    def write_document(self, filename, modules):
        path = self.installed / filename
        path.write_text(json.dumps({"modules": modules}), encoding="utf-8")
        return path

    def test_installed_reads_all_json_documents_preserving_module_metadata(self):
        self.write_document("a.json", [{"name": "first", "dir": "plugin", "version": "1"}])
        self.write_document("b.json", [{"name": "second", "dir": "other"}])
        (self.installed / "skip.txt").write_text("invalid json")
        (self.installed / "directory.json").mkdir()
        with patch.object(self.application.modules_service.runtime_client, "list_modules") as runtime:
            result = self.application.modules(installed=True)
        self.assertEqual(result["modules"], [
            {"name": "first", "dir": "plugin", "version": "1"},
            {"name": "second", "dir": "other"},
        ])
        runtime.assert_not_called()

    def test_existing_resources_document_needs_no_schema_change(self):
        source = ROOT / "resources/agents-system.json"
        (self.installed / source.name).write_bytes(source.read_bytes())
        self.assertEqual(self.application.modules(installed=True)["modules"], json.loads(source.read_text())["modules"])

    def test_identical_modules_are_deduplicated(self):
        for filename in ("a.json", "b.json"):
            self.write_document(filename, [{"name": "one", "dir": "one"}])
        self.assertEqual(len(self.application.modules(installed=True)["modules"]), 1)

    def test_conflicting_or_malformed_documents_fail_cleanly(self):
        self.write_document("a.json", [{"name": "one", "dir": "first"}])
        second = self.write_document("b.json", [{"name": "one", "dir": "second"}])
        with self.assertRaises(self.errors.ConfigurationError):
            self.application.modules(installed=True)
        for document in ('{"modules": {}}', '{invalid', '{"modules": [{}]}'):
            second.write_text(document)
            with self.assertRaises(self.errors.ConfigurationError):
                self.application.modules(installed=True)

    def test_missing_directory_is_an_empty_installation(self):
        self.configuration.__class__.INSTALLED_MODULES_DIR = str(self.base / "absent")
        self.assertEqual(self.application.modules(installed=True)["modules"], [])

    def test_installed_path_must_be_an_absolute_directory(self):
        for path in ("relative", str(self.write_document("file.json", []))):
            self.configuration.__class__.INSTALLED_MODULES_DIR = path
            with self.assertRaises(self.errors.ConfigurationError):
                self.application.modules(installed=True)

    def test_wrapper_returns_serializable_sorted_public_running_instances(self):
        class Plugin:
            pass
        manager = InstanceManager()
        for name in ("z-plugin", "configuration_block", "a-plugin"):
            manager.register(name, Plugin, Plugin())
        result = InstanceManagerWrapper(manager).get_running_modules()
        self.assertEqual(result, {"modules": [
            {"name": "a-plugin", "class": "Plugin"},
            {"name": "z-plugin", "class": "Plugin"},
        ]})
        json.dumps(result)

    def test_running_queries_instance_manager_wrapper_and_never_reads_installed(self):
        gateway = Mock()
        gateway.call.return_value = {"modules": [{"name": "plugin"}]}
        with patch.object(self.runtime_module, "RuntimeSocketGateway", return_value=gateway), patch.object(self.application.modules_service.installed_reader, "list_modules") as reader:
            result = self.application.modules(running=True)
        self.assertEqual(result["modules"], [{"name": "plugin"}])
        gateway.call.assert_called_once_with("instance-manager", "get_running_modules")
        reader.assert_not_called()

    def test_down_runtime_is_an_error_instead_of_an_installed_list(self):
        gateway = Mock()
        gateway.call.side_effect = RuntimeUnavailableError("refused")
        with patch.object(self.runtime_module, "RuntimeSocketGateway", return_value=gateway):
            with self.assertRaisesRegex(self.errors.ApiError, "Application runtime does not working"):
                self.application.modules(running=True)

    def test_runtime_failure_or_invalid_response_is_reported(self):
        gateway = Mock()
        with patch.object(self.runtime_module, "RuntimeSocketGateway", return_value=gateway):
            for value in ({}, {"modules": [None]}, {"modules": "invalid"}):
                gateway.call.return_value = value
                with self.assertRaises(self.errors.ApiError):
                    self.application.modules(running=True)
            gateway.call.side_effect = RuntimeCallError("internal error")
            with self.assertRaisesRegex(self.errors.ApiError, "Runtime nie działa poprawnie"):
                self.application.modules(running=True)

    def test_api_and_parser_require_exactly_one_flag(self):
        for options in ({}, {"installed": True, "running": True}):
            with self.assertRaises(self.errors.InputError):
                self.application.modules(**options)
        from agents_system_cli.app.exceptions import ApiError as ParserError
        console = importlib.import_module(self.application.__class__.__module__.rsplit(".", 1)[0] + ".console").Console
        for argv in ([], ["--installed", "--running"], ["--unknown"]):
            with self.assertRaises(ParserError):
                console.execute(["modules", *argv], application=self.application)
        self.assertIn("--running", console.execute(["modules", "--help"], application=self.application).stdout)
        self.assertEqual(console.execute(["--json", "modules", "--installed"], application=self.application).data["modules"], [])

    def test_asystem_dispatches_installed_from_template_dynamically(self):
        self.write_document("a.json", [{"name": "plugin", "dir": "plugin"}])
        console = ConsoleApplication(self.configuration)
        result = console.run(["--json", "system", "modules", "--installed"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(json.loads(result.stdout)["modules"], [{"name": "plugin", "dir": "plugin"}])
        invalid = console.run(["system", "modules", "--installed", "--running"])
        self.assertEqual(invalid.exit_code, 2)

    def test_asystem_running_reports_down_runtime_in_red(self):
        with patch("sys.stdout.isatty", return_value=True), patch.dict("os.environ", {}, clear=True):
            result = ConsoleApplication(self.configuration).run(["system", "modules", "--running"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Application runtime does not working", result.stderr)
        self.assertIn("\033[31m", result.stderr)
        self.assertNotIn("Running in local mode", result.stdout)

    def test_rendering_preserves_new_source_command_and_flags(self):
        template = ROOT / "resources/agents-system.module.template.json"
        before = template.read_bytes()
        output = self.base / "rendered.json"
        # A complete installed module tree, isolated from the in-progress
        # source migration of runtime -> _runtime.
        module_tree = self.base / "modules"
        for child in json.loads(before)["children"]:
            (module_tree / child["absolute_module_path"].removeprefix("${MODULES_DIR}/")).mkdir(parents=True)
        render(package_dir=ROOT, app_dir=ROOT, modules_dir=module_tree, manifest_path=output, output=output, force=False)
        document = json.loads(output.read_text())
        section = next(child for child in document["children"] if child["section_name"] == "system")
        command = next(command for command in section["commands"] if command["name"] == "modules")
        self.assertEqual(FlagParser.parse(command, ["--installed"]), {"installed": True, "running": False})
        self.assertEqual(template.read_bytes(), before)

    def test_running_reads_wrapper_response_over_a_real_unix_socket(self):
        class Plugin:
            pass
        manager = InstanceManager()
        manager.register("example-plugin", Plugin, Plugin())
        wrapper = InstanceManagerWrapper(manager)
        socket_path = self.base / "runtime.sock"
        self.configuration.__class__.SYSTEM_AGENT_RUNTIME_SOCKET = str(socket_path)
        ready = threading.Event()
        received = []
        failures = []

        def serve_once():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.settimeout(2)
                    server.bind(str(socket_path))
                    server.listen(1)
                    ready.set()
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(2)
                        with connection.makefile("rb") as reader:
                            request = json.loads(reader.readline())
                        received.append(request)
                        self.assertEqual(request["service"], "instance-manager")
                        response = getattr(wrapper, request["method"])(*request["args"], **request["kwargs"])
                        connection.sendall((json.dumps({"ok": True, "result": response}) + "\n").encode())
            except Exception as exc:
                failures.append(exc)
                ready.set()

        worker = threading.Thread(target=serve_once, daemon=True)
        worker.start()
        self.assertTrue(ready.wait(timeout=2))
        if failures:
            raise failures[0]
        result = self.application.modules(running=True)
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(result["modules"], [{"name": "example-plugin", "class": "Plugin"}])
        self.assertEqual(received[0]["method"], "get_running_modules")
