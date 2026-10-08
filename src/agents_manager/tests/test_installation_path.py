"""Installation selects an explicit directory before changing host state."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from agents_manager.app.services.agent_services_factory import AgentServicesFactory
from agents_manager.app.services.agents_installator_service import AgentsInstallatorService
from agents_system_cli.app.exceptions import ApiError
from agents_system_cli.app.services.flag_parser import FlagParser
from lib.modules_catalog import Command, Flag
from manifests.app.helpers.manifest_validator import ManifestValidator


class InstallationPathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "external definitions" / "example"
        self.source.mkdir(parents=True)
        self.context = SimpleNamespace(
            agents_root=self.root / "repository" / "agents",
            state_root=self.root / "state", gateway_user="gateway",
        )
        self.factory = Mock()
        self.installer = AgentsInstallatorService(self.factory)

    @staticmethod
    def install_command() -> Command:
        path = Path(__file__).resolve().parents[1] / "resources" / "agents_manager.module.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        ManifestValidator.validate(document)
        definition = next(command for command in document["commands"] if command["name"] == "install")
        return Command(
            name=definition["name"], method=definition.get("method"),
            description=definition["description"], usage=definition["usage"],
            implementation_status=definition["implementation_status"],
            flags=[Flag(**flag) for flag in definition["flags"]],
        )

    def test_cli_parses_short_long_and_inline_path_without_splitting_spaces(self):
        command = self.install_command()
        path = str(self.source)
        for argv in (["-p", path], ["--path", path], [f"--path={path}"]):
            with self.subTest(argv=argv):
                flags = {flag.name: flag.value for flag in FlagParser.parse(command, argv)}
                self.assertEqual(flags["path"], path)
        self.assertTrue(next(flag for flag in command.flags if flag.name == "path").required)

    def test_cli_rejects_missing_path_or_value(self):
        command = self.install_command()
        for argv in ([], ["--name", "example"], ["-p"], ["--path"]):
            with self.subTest(argv=argv):
                with self.assertRaisesRegex(ApiError, "--path"):
                    FlagParser.parse(command, argv)

    def test_invalid_source_is_rejected_before_creating_installation_dependencies(self):
        file_path = self.root / "file"
        file_path.write_text("ordinary file", encoding="utf-8")
        invalid_name = self.root / "invalid agent"
        invalid_name.mkdir()
        cases = (
            ({}, ValueError),
            ({"path": ""}, ValueError),
            ({"path": True}, ValueError),
            ({"path": str(self.root / "missing")}, FileNotFoundError),
            ({"path": str(file_path)}, NotADirectoryError),
            ({"path": str(invalid_name)}, ValueError),
            ({"path": str(self.source), "name": "different"}, ValueError),
        )
        for flags, error in cases:
            with self.subTest(flags=flags):
                with self.assertRaises(error):
                    self.installer.execute(flags, self.context)
        self.factory.create.assert_not_called()
        self.assertFalse(self.context.state_root.exists())

    def test_missing_template_is_rejected_before_preparing_state_or_users(self):
        services = self.factory.create.return_value
        services.configuration.resolve.return_value = SimpleNamespace(name="example", user=None, model=None)
        with self.assertRaisesRegex(FileNotFoundError, "Missing shell template"):
            self.installer.execute({"path": str(self.source)}, self.context)
        services.state.prepare.assert_not_called()
        services.linux_users.resolve_or_create.assert_not_called()

    def test_factory_loads_selected_external_config_without_changing_shared_context(self):
        (self.source / "config.json").write_text(json.dumps({
            "name": "example", "model": "selected-model", "default": False,
        }), encoding="utf-8")
        configuration = type("Configuration", (), {"APP_DIR": str(self.root / "repository")})()
        factory = AgentServicesFactory(configuration, Mock())
        with redirect_stdout(io.StringIO()):
            selected = factory.create(self.context, {"path": str(self.source)})
            regular = factory.create(self.context, {})
        definition = selected.configuration.resolve(self.source.name)
        self.assertEqual(definition.model, "selected-model")
        self.assertEqual(definition.source, self.source / "config.json")
        self.assertEqual(selected.catalog.agents_root, self.source.parent)
        self.assertEqual(regular.catalog.agents_root, self.context.agents_root)
        self.assertEqual(self.context.agents_root, self.root / "repository" / "agents")

    def test_update_uses_recorded_external_source(self):
        state_dir = self.context.state_root / "example"
        state_dir.mkdir(parents=True)
        (state_dir / "config.json").write_text(json.dumps({
            "name": "example", "definition_path": str(self.source),
        }), encoding="utf-8")
        self.assertEqual(self.installer._definition_path({
            "name": "example", "operation": "update",
        }, self.context), self.source)

    def test_update_preserves_source_for_older_installations(self):
        legacy_source = self.context.agents_root / "example"
        legacy_source.mkdir(parents=True)
        flags = {"name": "example", "operation": "update"}
        self.assertEqual(self.installer._definition_path(flags, self.context), legacy_source)
        state_dir = self.context.state_root / "example"
        state_dir.mkdir(parents=True)
        (state_dir / "config.json").write_text('{"name": "example"}', encoding="utf-8")
        self.assertEqual(self.installer._definition_path(flags, self.context), legacy_source)


if __name__ == "__main__":
    unittest.main()
