"""Manifest console, control-plane boundary and runtime registration tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from app_api.app.application import Application  # noqa: E402
from app_api.app.models import ApiResult  # noqa: E402
from app_api.main import create_service, execute  # noqa: E402
from app_api.app.services.manifests import ManifestCatalog  # noqa: E402


class NoRuntime:
    def execute(self, _arguments):
        return None


class FakeControlPlane:
    def __init__(self) -> None:
        self.envelope = None

    def dispatch(self, envelope):
        self.envelope = envelope
        return {
            "ok": True,
            "status": "not-implemented",
            "message": "Not implemented yet.",
            "target": {
                "section": envelope["section"],
                "module_name": envelope["module_name"],
                "command": envelope["command"],
            },
        }


class AppApiTests(unittest.TestCase):
    def application(self) -> tuple[Application, FakeControlPlane]:
        application = Application(ROOT)
        application.runtime = NoRuntime()
        control_plane = FakeControlPlane()
        application.control_plane = control_plane
        return application, control_plane

    def test_catalog_builds_menu_only_in_memory(self) -> None:
        path = ROOT / "resources" / "agents-system.module.template.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        merged = ManifestCatalog(path).load()

        self.assertNotIn("sections", source)
        self.assertEqual(set(merged["sections"]), {"agents", "system"})
        self.assertEqual(merged["sections"]["agents"]["module_name"], "agents-manager")
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["children"],
            source["children"],
        )

    def test_main_only_delegates_to_application(self) -> None:
        class StubApplication:
            arguments = None

            def run(self, arguments):
                self.arguments = arguments
                return ApiResult(stdout="delegated\n")

        application = StubApplication()
        result = execute(["agents"], application=application)

        self.assertEqual(application.arguments, ["agents"])
        self.assertEqual(result.stdout, "delegated\n")

    def test_application_decides_whether_to_use_runtime(self) -> None:
        application, control_plane = self.application()

        class ResidentRuntime:
            def execute(self, arguments):
                return ApiResult(stdout="resident\n", data={"arguments": arguments})

        application.runtime = ResidentRuntime()
        result = application.run(["agents"])

        self.assertEqual(result.stdout, "resident\n")
        self.assertIsNone(control_plane.envelope)

    def test_hierarchical_help_is_contextual(self) -> None:
        application, _ = self.application()

        self.assertIn("Sekcje:", application.run(["--human-raw"]).stdout)
        self.assertIn("Komendy:", application.run(["--human-raw", "agents"]).stdout)
        command_help = application.run(["--human-raw", "agents", "install", "--help"]).stdout
        self.assertIn("asystem agents install", command_help)
        self.assertIn("--dry-run", command_help)

    def test_agent_mode_is_compact_json(self) -> None:
        application, _ = self.application()
        result = application.run(["--agent", "agents"])
        value = json.loads(result.stdout)

        self.assertEqual(value["kind"], "asystem-agent-section")
        self.assertEqual(value["path"], ["agents"])
        self.assertNotIn("\n  ", result.stdout)

    def test_command_is_validated_then_forwarded_to_control_plane(self) -> None:
        application, control_plane = self.application()
        result = application.run(["--human-raw", "agents", "install", "-n", "huggin", "--dry-run"])

        self.assertEqual(result.stdout, "Not implemented yet.\n")
        self.assertEqual(control_plane.envelope["module_name"], "agents-manager")
        self.assertEqual(control_plane.envelope["arguments"]["name"], "huggin")
        self.assertTrue(control_plane.envelope["arguments"]["dry_run"])

    def test_invalid_or_missing_required_flags_are_clean_errors(self) -> None:
        application, _ = self.application()

        missing = application.run(["agents", "update"])
        unknown = application.run(["agents", "install", "--unknown"])

        self.assertEqual(missing.exit_code, 2)
        self.assertIn("wymaga --name", missing.stderr)
        self.assertEqual(unknown.exit_code, 2)
        self.assertNotIn("Traceback", unknown.stderr)

    def test_resident_handler_uses_same_application(self) -> None:
        result = create_service()({"args": ["--agent"]})
        value = json.loads(result["stdout"])

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(value["kind"], "asystem-agent-menu")

    def test_real_control_plane_returns_placeholder(self) -> None:
        application = Application(ROOT)
        application.runtime = NoRuntime()
        result = execute(
            ["--human-raw", "agents", "install"],
            application=application,
        )

        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stdout, "Not implemented yet.\n")



if __name__ == "__main__":
    unittest.main()
