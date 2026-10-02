"""Manifest-driven invocation of arbitrary application modules and methods."""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from app_api.app.application import Application
from app_api.app.exceptions import ApiError
from app_api.app.services.module_dispatcher import ModuleDispatcher
from app_api.app.services.flag_parser import FlagParser
from shared.socket_client import RuntimeCallError
from shared.socket_client import RuntimeUnavailableError
from shared.socket_client import RuntimeResponse

runtime = importlib.import_module("app_api.app.services.runtime")


class ModuleDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        module = self.root / "dynamic-app"
        (module / "app").mkdir(parents=True)
        (module / "meta.json").write_text(json.dumps({
            "namespace": "dynamic", "entrypoint": "main.py",
            "application": {"module": "app.application", "class": "CustomApplication"},
        }))
        (module / "app/helper.py").write_text('def report(name, count):\n    return {"name": name, "count": count}\n')
        (module / "app/application.py").write_text('''from .helper import report
class CustomApplication:
    def __init__(self, configuration):
        self.configuration = configuration
        self.calls = 0
    def inspect(self, name, count=1):
        self.calls += 1
        return report(name, count)
''')
        self.command = {
            "name": "check-new", "method": "inspect", "description": "Read data",
            "usage": "asystem arbitrary check-new --name NAME", "flags": [
                {"name": "name", "long": "--name", "takes_value": True,
                 "required": True, "type": "string", "description": "Name", "usage": "--name NAME"},
                {"name": "count", "long": "--count", "takes_value": True,
                 "default": 1, "type": "integer", "description": "Count", "usage": "--count NUMBER"},
            ],
        }
        self.section = {
            "module_name": "new-module", "section_name": "arbitrary", "is_menu_option": True,
            "is_runtime": False, "runtime": ["main"], "menu_name": "New menu",
            "description": "A new module", "absolute_module_path": "${MODULES_DIR}/dynamic-app",
            "commands": [self.command],
        }
        manifest = self.root / "modules.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "version": 1, "kind": "agents-system-modules-manifest",
            "app_module_name": "agents-system", "manifest_absolute_path": str(manifest),
            "children": [self.section],
        }))
        class Configuration:
            APP_DIR = str(self.root)
            MODULES_DIR = str(self.root)
            MODULES_MANIFEST_PATH = str(manifest)
            SYSTEM_AGENT_RUNTIME_SOCKET = str(self.root / "missing.sock")
            MAX_MESSAGE_BYTES_BASE = "1024"
            MAX_MESSAGE_BYTES_MULTIPLIER = "1024"
        self.configuration = Configuration()

    def test_new_section_and_method_execute_locally_without_application_changes(self):
        application = Application(self.configuration)
        with patch.object(application.dispatcher.runtime, "is_available", return_value=False):
            result = application.run(["--json", "arbitrary", "check-new", "--name", "a b", "--count", "3"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(json.loads(result.stdout), {"name": "a b", "count": 3})
        instance = application.dispatcher.loader.load(self.section)
        self.assertIs(instance.configuration, self.configuration)
        self.assertEqual(instance.calls, 1)
        self.assertIs(application.dispatcher.loader.load(self.section), instance)

    def test_runtime_receives_module_method_and_typed_arguments(self):
        gateway = Mock()
        gateway.call.side_effect = [{"APP_NAME": "agents-system"}, ["a", 3]]
        with patch.object(runtime, "RuntimeSocketGateway", return_value=gateway):
            application = Application(self.configuration)
            with patch.object(application.dispatcher.loader, "load") as load:
                result = application.run(["--json", "arbitrary", "check-new", "--name", "a", "--count", "3"])
        self.assertEqual(json.loads(result.stdout), ["a", 3])
        gateway.call.assert_called_with("new-module", "inspect", kwargs={"name": "a", "count": 3})
        load.assert_not_called()

    def test_missing_socket_executes_selected_module_locally(self):
        result = Application(self.configuration).run(["--json", "arbitrary", "check-new", "--name", "local"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.data, {"name": "local", "count": 1})

    def test_connection_failure_before_command_falls_back(self):
        gateway = Mock()
        gateway.call.side_effect = [{}, RuntimeUnavailableError("connection refused")]
        with patch.object(runtime, "RuntimeSocketGateway", return_value=gateway):
            application = Application(self.configuration)
            result = application.run(["--json", "arbitrary", "check-new", "--name", "local"])
        self.assertEqual(result.data, {"name": "local", "count": 1})
        self.assertFalse(application.runtime_available)

    def test_runtime_action_failure_never_invokes_local_module(self):
        gateway = Mock()
        gateway.call.side_effect = [{}, RuntimeCallError("response lost")]
        with patch.object(runtime, "RuntimeSocketGateway", return_value=gateway):
            application = Application(self.configuration)
            with patch.object(application.dispatcher.loader, "load") as load:
                result = application.run(["arbitrary", "check-new", "--name", "a"])
        self.assertEqual(result.exit_code, 1)
        load.assert_not_called()

    def test_missing_method_is_an_error_for_an_unadapted_module(self):
        dispatcher = ModuleDispatcher(self.configuration)
        with patch.object(dispatcher.runtime, "is_available", return_value=False):
            with self.assertRaisesRegex(ApiError, "nie udostępnia metody unknown"):
                dispatcher.dispatch(self.section, {"name": "unknown"}, {})

    def test_method_name_defaults_to_command_with_underscores(self):
        dispatcher = ModuleDispatcher(self.configuration)
        with patch.object(dispatcher.runtime, "is_available", return_value=True), patch.object(dispatcher.runtime, "call") as call:
            dispatcher.dispatch(self.section, {"name": "get-details"}, {"count": 2})
        call.assert_called_once_with("new-module", "get_details", {"count": 2})

    def test_private_method_is_rejected_before_loading_or_runtime(self):
        dispatcher = ModuleDispatcher(self.configuration)
        with patch.object(dispatcher.runtime, "is_available") as probe:
            with self.assertRaises(ApiError):
                dispatcher.dispatch(self.section, {"name": "inspect", "method": "_private"}, {})
        probe.assert_not_called()

    def test_runtime_response_preserves_arbitrary_json_values(self):
        for value in ([1, "a"], "message", False, 0, None, {"count": 2}):
            self.assertEqual(RuntimeResponse({"ok": True, "result": value}).result, value)

    def test_parser_passes_positionals_and_rejects_invalid_integer(self):
        command = {"name": "lookup", "flags": [], "positionals": [{"name": "name", "required": True}]}
        self.assertEqual(FlagParser.parse(command, ["two words"]), {"name": "two words"})
        with self.assertRaises(ApiError):
            FlagParser.parse(self.command, ["--name", "a", "--count", "invalid"])

    def test_manifest_parameter_name_is_independent_of_cli_flag_name(self):
        self.command["flags"][0].update(long="--display-title", short="-x", aliases=["--label"])
        manifest = self.root / "modules.json"
        document = json.loads(manifest.read_text())
        document["children"][0]["commands"] = [self.command]
        manifest.write_text(json.dumps(document))
        for token in ("--display-title", "-x", "--label"):
            result = Application(self.configuration).run(["--json", "arbitrary", "check-new", token, "custom"])
            self.assertEqual(result.data, {"name": "custom", "count": 1})

    def test_console_option_used_as_value_is_preserved(self):
        result = Application(self.configuration).run(["--json", "arbitrary", "check-new", "--name", "--interactive"])
        self.assertEqual(result.data, {"name": "--interactive", "count": 1})

    def test_plugin_flags_matching_console_options_are_forwarded(self):
        self.command["flags"].append({
            "name": "plugin_interactive", "long": "--interactive", "takes_value": False,
            "description": "Plugin flag", "usage": "--interactive", "type": "boolean",
        })
        manifest = self.root / "modules.json"
        document = json.loads(manifest.read_text())
        document["children"][0]["commands"] = [self.command]
        manifest.write_text(json.dumps(document))
        gateway = Mock()
        gateway.call.side_effect = [{}, {"plugin_interactive": True}]
        with patch.object(runtime, "RuntimeSocketGateway", return_value=gateway):
            result = Application(self.configuration).run(["--json", "arbitrary", "check-new", "--name", "custom", "--interactive"])
        self.assertEqual(result.data, {"plugin_interactive": True})
        gateway.call.assert_called_with("new-module", "inspect", kwargs={"name": "custom", "count": 1, "plugin_interactive": True})

    def test_positional_separator_preserves_console_flag_as_data(self):
        self.command["flags"] = []
        self.command["positionals"] = [{"name": "name", "required": True}]
        manifest = self.root / "modules.json"
        document = json.loads(manifest.read_text())
        document["children"][0]["commands"] = [self.command]
        manifest.write_text(json.dumps(document))
        result = Application(self.configuration).run(["--json", "arbitrary", "check-new", "--", "--help"])
        self.assertEqual(result.data, {"name": "--help", "count": 1})
