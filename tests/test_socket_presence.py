"""Socket presence and safe local fallback, using isolated paths."""
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from agents_system_cli import AgentsSystemCLI
from agents_system_cli.app.services import ModuleDispatcher
from lib.unix_socket import SocketClientBuilder, SocketConfiguration
from lib.unix_socket.exceptions import UnixSocketConnectionException


class SocketPresenceTests(unittest.TestCase):
    def test_missing_regular_file_and_socket_before_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.sock"
            client = SocketClientBuilder.create(SocketConfiguration(path, 1, 1, 1024)).get()
            self.assertFalse(client.socket_exists())
            path.write_text("ordinary file")
            self.assertFalse(client.socket_exists())
            path.unlink()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(path))
                self.assertTrue(client.socket_exists())
                self.assertFalse(client.is_connected)

    def initialize(self, client):
        class Settings:
            SYSTEM_AGENT_RUNTIME_SOCKET = "/run/example/runtime.sock"
            MAX_MESSAGE_BYTES_BASE = 1024
            MAX_MESSAGE_BYTES_MULTIPLIER = 1
            MODULES_MANIFEST_PATH = "/unused/manifest.json"
        with patch("agents_system_cli.app.application.SocketClientBuilder") as builder, \
             patch("agents_system_cli.app.application.ModulesFactory.create_modules_from_json_file"), \
             patch("agents_system_cli.app.application.RenderersFactory"):
            builder.return_value.create.return_value.get.return_value = client
            return AgentsSystemCLI(Settings())

    def test_missing_socket_initializes_and_dispatches_locally(self):
        client = Mock(is_connected=False)
        client.socket_exists.return_value = False
        app = self.initialize(client)
        client.connect.assert_not_called()
        self.assertFalse(app.runtime_available())
        app.dispatcher.loader = Mock()
        app.dispatcher.loader.load.return_value.modules.return_value = {"installed": []}
        result = app.dispatcher.dispatch(SimpleNamespace(module_name="system"),
                                         SimpleNamespace(method="modules", name="modules"), [])
        self.assertEqual(result, {"installed": []})
        client.is_healthy.assert_not_called()
        client.send.assert_not_called()

    def test_existing_socket_connects(self):
        client = Mock()
        client.socket_exists.return_value = True
        self.initialize(client)
        client.connect.assert_called_once_with()

    def test_socket_disappearing_before_connect_allows_local_mode(self):
        client = Mock(is_connected=False)
        client.socket_exists.return_value = True
        error = UnixSocketConnectionException("missing")
        error.__cause__ = FileNotFoundError("missing")
        client.connect.side_effect = error
        self.assertFalse(self.initialize(client).runtime_available())

    def test_other_connection_errors_propagate(self):
        client = Mock()
        client.socket_exists.return_value = True
        client.connect.side_effect = UnixSocketConnectionException("permission denied")
        with self.assertRaises(UnixSocketConnectionException):
            self.initialize(client)

    def test_request_failure_never_falls_back(self):
        client = Mock(is_connected=True)
        client.is_healthy.return_value = True
        client.send.side_effect = UnixSocketConnectionException("lost response")
        dispatcher = ModuleDispatcher(object(), client)
        dispatcher.loader = Mock()
        with self.assertRaises(UnixSocketConnectionException):
            dispatcher.dispatch(SimpleNamespace(module_name="system"),
                                SimpleNamespace(method="modules", name="modules"), [])
        dispatcher.loader.load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
