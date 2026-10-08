"""Contract tests for the runtime message-size environment values."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESSAGE_SIZE_NAMES = {
    "MAX_MESSAGE_BYTES_BASE",
    "MAX_MESSAGE_BYTES_MULTIPLIER",
}


class RuntimeMessageSizeConfigurationTests(unittest.TestCase):
    def test_renderer_manages_every_template_variable(self) -> None:
        template = json.loads(
            (ROOT / "resources" / "app_env.template.json").read_text(encoding="utf-8")
        )
        contract = json.loads(
            (ROOT / "internal_scripts" / "render-app-env.json").read_text(encoding="utf-8")
        )
        template_names = {item["name"] for item in template["variables"]}
        managed_names = {item["name"] for item in contract["managed_variables"]}

        self.assertEqual(template_names, managed_names)
        self.assertTrue(MESSAGE_SIZE_NAMES <= managed_names)

    def test_message_size_values_are_fixed_template_inputs(self) -> None:
        contract = json.loads(
            (ROOT / "internal_scripts" / "render-app-env.json").read_text(encoding="utf-8")
        )
        managed = {item["name"]: item for item in contract["managed_variables"]}

        for name in MESSAGE_SIZE_NAMES:
            self.assertEqual(managed[name]["value"], "1024")
            self.assertEqual(managed[name]["source"], "app_env.template.json")
            self.assertTrue(managed[name]["required"])


if __name__ == "__main__":
    unittest.main()

