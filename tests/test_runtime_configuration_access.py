"""Runtime reads generated configuration fields through their class."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lib.configuration import Configuration
from _runtime.app.instance_manager import InstanceManager
from _runtime.app.main_runtime import MainRuntime


class RuntimeConfigurationAccessTests(unittest.TestCase):
    def test_initialization_reads_class_only_socket_and_message_limit(self):
        class RuntimeConfiguration(Configuration):
            pass

        values = {
            item["name"]: item["value"]
            for item in json.loads((ROOT / "resources/app_env.template.json").read_text())["variables"]
        }
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "runtime.sock"
            values.update(SYSTEM_AGENT_RUNTIME_SOCKET=str(socket_path),
                          MAX_MESSAGE_BYTES_BASE="2048", MAX_MESSAGE_BYTES_MULTIPLIER="16")
            configuration = RuntimeConfiguration(values)
            with self.assertRaises(AttributeError):
                _ = configuration.SYSTEM_AGENT_RUNTIME_SOCKET
            runtime = MainRuntime(InstanceManager(), configuration)
            try:
                self.assertIs(runtime.configuration, configuration)
                self.assertEqual(runtime._socket_path, socket_path)
                self.assertEqual(runtime.MAX_MESSAGE_BYTES, 2048 * 16)
                self.assertFalse(socket_path.exists())
            finally:
                runtime._dispatcher.shutdown()
