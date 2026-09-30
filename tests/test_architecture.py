from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXED_ENTRYPOINTS = {
    "agents-system": "src/agents-system/main.py",
    "runtime": "src/runtime/main.py",
    "agents-data-runtime": "src/agents-data-runtime/main.py",
    "app_api": "src/app_api/main.py",
    "agents-manager": "src/agents-manager/main.py",
    "agents-data": "src/agents-data/main.py",
    "agents-data-backend": "src/agents-data-backend/main.py",
}


class ArchitectureContractTests(unittest.TestCase):
    def test_fixed_application_entrypoints_exist(self) -> None:
        for application, relative_path in FIXED_ENTRYPOINTS.items():
            with self.subTest(application=application):
                self.assertTrue((REPOSITORY_ROOT / relative_path).is_file())

    def test_manifest_uses_fixed_entrypoints(self) -> None:
        manifest = json.loads((REPOSITORY_ROOT / "manifest.json").read_text())
        declared = {
            application["id"]: application["entrypoint"]
            for application in manifest["applications"]
        }
        self.assertEqual(FIXED_ENTRYPOINTS, declared)

    def test_underscore_source_tree_does_not_exist(self) -> None:
        self.assertFalse((REPOSITORY_ROOT / "src" / "agents_system").exists())

    def test_app_api_uses_application_and_service_layers(self) -> None:
        root = REPOSITORY_ROOT / "src" / "app_api"
        self.assertTrue((root / "app" / "application.py").is_file())
        for service in ("control_plane.py", "manifests.py", "renderer.py", "runtime.py"):
            self.assertTrue((root / "app" / "services" / service).is_file())
        for flat_module in ("application.py", "control_plane.py", "manifests.py", "models.py", "renderer.py"):
            self.assertFalse((root / flat_module).exists())

    def test_host_wrappers_use_canonical_control_plane(self) -> None:
        for wrapper in (REPOSITORY_ROOT / "host_scripts").glob("*.sh"):
            with self.subTest(wrapper=wrapper.name):
                content = wrapper.read_text()
                self.assertNotIn("src/agents_system/", content)
                expected = "src/app_api/main.py" if wrapper.name == "asystem.sh" else "src/agents-system/main.py"
                self.assertIn(expected, content)

    def test_architecture_links_both_merge_plans(self) -> None:
        architecture = (REPOSITORY_ROOT / "ARCHITECTURE.md").read_text()
        self.assertIn("AGENT_MANAGER_MERGE.md", architecture)
        self.assertIn("COMMUNICATION_STACK_MERGE.md", architecture)


    def test_migrated_applications_use_application_layers(self) -> None:
        self.assertTrue(
            (REPOSITORY_ROOT / "src" / "agents-manager" / "app" / "application.py").is_file()
        )
        self.assertTrue(
            (REPOSITORY_ROOT / "src" / "agents-data" / "app" / "application.py").is_file()
        )
        self.assertTrue(
            (REPOSITORY_ROOT / "src" / "agents-data-runtime" / "service.py").is_file()
        )

    def test_agent_resources_and_provider_plugin_were_migrated(self) -> None:
        self.assertTrue((REPOSITORY_ROOT / "agents" / "shared" / "scripts").is_dir())
        self.assertFalse((REPOSITORY_ROOT / "agents" / "agents.py").exists())
        self.assertTrue(
            (REPOSITORY_ROOT / "provider_plugins" / "openclaw" / "agent-executor" / "openclaw.plugin.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
