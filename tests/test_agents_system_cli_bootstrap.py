"""Socket client initialization and package loading contracts."""

import importlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from agents_system_cli import AgentsSystemCLI
from agents_system_cli.app.exceptions import ApiError
from agents_system_cli.app.services import ModuleDispatcher, ModuleLoader, RuntimeDispatcher


ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def configuration(self, manifest):
        class Settings:
            MODULES_MANIFEST_PATH = manifest
            SYSTEM_AGENT_RUNTIME_SOCKET = "/nonexistent/agents-system.sock"
            MAX_MESSAGE_BYTES_BASE = 1024
            MAX_MESSAGE_BYTES_MULTIPLIER = 1024
        return Settings()

    def test_application_connects_during_construction(self):
        configuration = self.configuration(ROOT / "resources/agents-system.module.template.json")
        with patch("agents_system_cli.app.services.runtime.SocketClientBuilder") as builder:
            application = AgentsSystemCLI(configuration)
            self.assertIsNotNone(application.dispatcher)
            builder.return_value.create.return_value.get.return_value.connect.assert_called_once_with()

    def test_missing_socket_propagates_during_construction(self):
        with patch("agents_system_cli.app.services.runtime.SocketClientBuilder") as builder:
            client = builder.return_value.create.return_value.get.return_value
            client.connect.side_effect = FileNotFoundError("socket missing")
            with self.assertRaises(FileNotFoundError):
                RuntimeDispatcher(self.configuration("unused"))

    def test_runtime_response_returns_result(self):
        with patch("agents_system_cli.app.services.runtime.SocketClientBuilder") as builder:
            client = builder.return_value.create.return_value.get.return_value
            client.is_connected = False
            client.call.return_value = {"ok": True}
            runtime = RuntimeDispatcher(self.configuration("unused"))
            self.assertEqual(runtime.call("system", "status", {}), {"ok": True})
            client.connect.assert_called_once()

    def test_runtime_failure_never_executes_local_operation(self):
        dispatcher = ModuleDispatcher.__new__(ModuleDispatcher)
        dispatcher.runtime = Mock()
        dispatcher.runtime.call.side_effect = ApiError("transport failed")
        dispatcher.loader = Mock()
        dispatcher._runtime_available = True
        with self.assertRaises(ApiError):
            dispatcher.dispatch(SimpleNamespace(module_name="system"),
                                SimpleNamespace(name="status", method="show_status"), [])
        dispatcher.loader.load.assert_not_called()

    def test_local_entrypoint_supports_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "helper.py").write_text("def create(config):\n    return config\n")
            (root / "__main__.py").write_text(
                "from .helper import create\ndef get_main_app(config):\n    return create(config)\n"
            )
            configuration = object()
            instance = ModuleLoader(configuration).load(
                SimpleNamespace(absolute_module_path=directory, module_name="example")
            )
            self.assertIs(instance, configuration)

    def test_all_package_modules_import(self):
        for path in (ROOT / "src/agents_system_cli").rglob("*.py"):
            parts = list(path.relative_to(ROOT / "src").with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            importlib.import_module(".".join(parts))
