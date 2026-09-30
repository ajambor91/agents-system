"""Agents System runtime IPC and lazy-loading regression tests."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "src" / "agents-system" / "main.py"
RUNTIME_SERVICE = ROOT / "src" / "runtime" / "service.py"


def load_runtime():
    """Load the standalone runtime entrypoint for isolated tests."""
    spec = importlib.util.spec_from_file_location("agents_system_runtime_test", RUNTIME_SERVICE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = load_runtime()

    def test_peer_credentials_come_from_kernel(self) -> None:
        client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            peer = self.runtime.peer_credentials(server)
        finally:
            client.close()
            server.close()
        self.assertEqual(peer["peer_uid"], os.geteuid())
        self.assertEqual(peer["peer_gid"], os.getegid())
        self.assertGreater(peer["peer_pid"], 0)

    def test_missing_module_is_explicitly_safe_for_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self._set_paths(Path(temporary))
            response = self.runtime.handle_runtime_request(
                {"module": "missing", "payload": {}},
                {},
                {},
                {"peer_uid": os.geteuid()},
            )
        self.assertFalse(response["ok"])
        self.assertEqual(response["error_code"], "module_unavailable")

    def test_remove_unknown_module_is_a_clean_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = os.environ.copy()
            result = subprocess.run(
                [sys.executable, str(ENTRYPOINT), "app-remove", "--name", "ai_module"],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "Błąd: Nie ma zarejestrowanego modułu: ai_module\n",
        )
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_registered_module_loads_lazily_and_captures_streams(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._set_paths(root)
            repository = root / "repositories" / "sample"
            repository.mkdir(parents=True)
            entrypoint = repository / "main.py"
            entrypoint.write_text(
                "import sys\n"
                "def handle(payload):\n"
                "    print('module-out')\n"
                "    print('module-err', file=sys.stderr)\n"
                "    return {'peer_uid': payload['_runtime']['peer_uid']}\n",
                encoding="utf-8",
            )
            self.runtime.write_registry(
                {
                    "schema_version": 1,
                    "modules": {
                        "sample": {
                            "id": "sample",
                            "repository_path": str(repository),
                            "entrypoint": str(entrypoint),
                            "status": "registered",
                        }
                    },
                }
            )
            loaded = {}
            response = self.runtime.handle_runtime_request(
                {"module": "sample", "payload": {"value": 1}},
                loaded,
                {},
                {"peer_uid": os.geteuid()},
            )
            first_stamp = entrypoint.stat().st_mtime_ns
            entrypoint.write_text(
                "def handle(payload):\n"
                "    return {'version': 2}\n",
                encoding="utf-8",
            )
            os.utime(entrypoint, ns=(first_stamp + 1_000_000, first_stamp + 1_000_000))
            reloaded = self.runtime.handle_runtime_request(
                {"module": "sample", "payload": {}},
                loaded,
                {},
                {"peer_uid": os.geteuid()},
            )
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"], {"peer_uid": os.geteuid()})
        self.assertEqual(response["stdout"], "module-out\n")
        self.assertEqual(reloaded["result"], {"version": 2})
        self.assertEqual(response["stderr"], "module-err\n")
        self.assertIn("sample", loaded)

    def test_disconnected_client_does_not_raise_from_response_send(self) -> None:
        class DisconnectedSocket:
            def sendall(self, _payload):
                raise BrokenPipeError("client closed")

        self.assertFalse(
            self.runtime.send_runtime_response(
                DisconnectedSocket(),
                {"ok": True, "result": {"exit_code": 0}},
            )
        )

    def test_registry_is_written_under_repositories_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._set_paths(root)

            self.runtime.write_registry({"schema_version": 1, "modules": {}})

            self.assertTrue((root / ".repos" / "modules.json").is_file())
            self.assertFalse((root / ".agents" / "modules.json").exists())

    def test_app_api_is_a_builtin_runtime_module(self) -> None:
        registry = {"schema_version": 1, "modules": {}}

        self.runtime.register_builtin_modules(registry)

        record = registry["modules"]["app_api"]
        self.assertEqual(record["repository_path"], str(ROOT))
        self.assertEqual(record["entrypoint"], str(ROOT / "src" / "app_api" / "main.py"))

    def test_legacy_registry_is_migrated_to_repositories_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._set_paths(root)
            legacy = root / ".agents" / "modules.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(
                json.dumps({"schema_version": 1, "modules": {"sample": {"id": "sample"}}}),
                encoding="utf-8",
            )

            registry = self.runtime.read_registry()

            self.assertIn("sample", registry["modules"])
            self.assertTrue((root / ".repos" / "modules.json").is_file())
            self.assertFalse(legacy.exists())


    def _set_paths(self, root: Path) -> None:
        self.runtime.DEFAULT_ROOT = root / ".agents"
        self.runtime.MODULE_REGISTRY_ROOT = root / ".repos"
        self.runtime.REGISTRY_PATH = self.runtime.MODULE_REGISTRY_ROOT / "modules.json"
        self.runtime.LEGACY_REGISTRY_PATH = self.runtime.DEFAULT_ROOT / "modules.json"
        self.runtime.SOCKET_PATH = self.runtime.DEFAULT_ROOT / "runtime.sock"
        self.runtime.PID_PATH = self.runtime.DEFAULT_ROOT / "runtime.pid"


if __name__ == "__main__":
    unittest.main()
