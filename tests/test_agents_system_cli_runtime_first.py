"""Runtime-first agents_system_cli boundary and serializable wrapper tests."""

from __future__ import annotations

import importlib
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
LIBRARY_ROOT = SOURCE_ROOT / "lib"
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(LIBRARY_ROOT))

cli = importlib.import_module("agents_system_cli.__main__")

from agents_system_cli.app.application import AgentsSystemCLI  # noqa: E402
from agents_system_cli.app.models import ApiResult  # noqa: E402
from lib.configuration import ConfigurationWrapper  # noqa: E402
from shared.socket_client import RuntimeSocketGateway
from agents_system_cli.app.services.runtime import RuntimeDispatcher

console = importlib.import_module("agents_system_cli.app.console")
runtime = importlib.import_module("agents_system_cli.app.services.runtime")  # noqa: E402


class AgentsSystemCLIRuntimeFirstTests(unittest.TestCase):
    @staticmethod
    def configuration():
        class Settings:
            SYSTEM_AGENT_RUNTIME_SOCKET = "/tmp/runtime.sock"
            MAX_MESSAGE_BYTES_BASE = "32"
            MAX_MESSAGE_BYTES_MULTIPLIER = "32"
        return Settings()

    def test_execute_initializes_configuration_and_passes_it_to_application(self):
        configuration = object()
        application = Mock()
        application.run.return_value = ApiResult(stdout="menu\n")
        with (
            patch.object(console, "get_config", return_value=configuration) as get_config,
            patch.object(console, "AgentsSystemCLI", return_value=application) as factory,
        ):
            result = cli.execute(["agents"])
        get_config.assert_called_once_with()
        factory.assert_called_once_with(configuration)
        application.run.assert_called_once_with(["agents"])
        self.assertEqual(result.stdout, "menu\n")

    def test_configuration_wrapper_returns_plain_dictionary(self) -> None:
        class FakeConfiguration:
            NAME = "agents_system"
            LIMIT = 1024

            @classmethod
            def schema(cls):
                return {"NAME": str, "LIMIT": int}

        wrapper = ConfigurationWrapper(FakeConfiguration())

        self.assertEqual(
            wrapper.get_configuration_dict(),
            {"NAME": "agents_system", "LIMIT": 1024},
        )

    def test_application_exposes_json_serializable_runtime_method(self) -> None:
        application = object.__new__(AgentsSystemCLI)
        with patch.object(
            application,
            "run",
            return_value=ApiResult(stdout="agents list\n"),
        ):
            result = application.run_dict(["agents", "list"])

        self.assertEqual(result["stdout"], "agents list\n")
        self.assertEqual(result["exit_code"], 0)

    def test_gateway_uses_newline_delimited_runtime_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "runtime.sock"
            ready = threading.Event()
            received: list[dict[str, object]] = []

            def serve_once() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.bind(str(socket_path))
                    server.listen(1)
                    ready.set()
                    connection, _ = server.accept()
                    with connection:
                        frame = bytearray()
                        while b"\n" not in frame:
                            frame.extend(connection.recv(4096))
                        received.append(json.loads(frame.decode("utf-8")))
                        connection.sendall(
                            b'{"ok":true,"result":{"source":"runtime"}}\n'
                        )

            thread = threading.Thread(target=serve_once, daemon=True)
            thread.start()
            self.assertTrue(ready.wait(timeout=2))

            result = RuntimeSocketGateway(socket_path).call(
                "configuration",
                "get_configuration_dict",
            )
            thread.join(timeout=2)

        self.assertEqual(result, {"source": "runtime"})
        self.assertEqual(received[0]["service"], "configuration")
        self.assertEqual(received[0]["method"], "get_configuration_dict")

    def test_runtime_calls_selected_module_method_with_keyword_arguments(self):
        gateway = Mock()
        gateway.call.return_value = ["result"]
        with patch.object(runtime, "RuntimeSocketGateway", return_value=gateway):
            result = RuntimeDispatcher(self.configuration()).call("example", "inspect", {"name": "one"})
        self.assertEqual(result, ["result"])
        gateway.call.assert_called_once_with("example", "inspect", kwargs={"name": "one"})


if __name__ == "__main__":
    unittest.main()
