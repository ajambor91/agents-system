"""Environment schema, placeholder and CLI contract tests."""

from __future__ import annotations

import json
import os
import io
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
APPLICATION_ROOT = SOURCE_ROOT / "agents-system"
ENTRYPOINT = APPLICATION_ROOT / "main.py"
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(APPLICATION_ROOT))

from app.command import Command  # noqa: E402
from app.errors import ConfigurationError  # noqa: E402
from app.services.environment import EnvironmentService  # noqa: E402
from app.services.installation import InstallationService  # noqa: E402
from shared.configuration import ApplicationEnvironment  # noqa: E402


def document(system_home: Path, mode: str = "system") -> dict:
    config_dir = system_home / "config"
    data_dir = system_home / "data"
    runtime_dir = system_home / "run"
    return {
        "schema_version": 1,
        "kind": "agents-system-environment",
        "variables": [
            {"name": "USER_SYSTEM", "value": "tester", "description": "System user.", "example": "tester"},
            {"name": "USER_SYSTEM_HOME", "value": str(system_home), "description": "System home.", "example": str(system_home)},
            {"name": "INSTALL_MODE", "value": mode, "description": "Install mode.", "example": mode},
            {"name": "BASH_SOURCE", "value": "true", "description": "Shell precedence switch.", "example": "true"},
            {"name": "APP_NAME", "value": "agents-system", "description": "Application name.", "example": "agents-system"},
            {"name": "APP_DIR", "value": str(system_home / "app"), "description": "Application directory.", "example": str(system_home / "app")},
            {"name": "APP_CONFIG_DIR", "value": str(config_dir), "description": "Config directory.", "example": str(config_dir)},
            {"name": "APP_DATA_DIR", "value": str(data_dir), "description": "Data directory.", "example": str(data_dir)},
            {"name": "APP_RUNTIME_DIR", "value": str(runtime_dir), "description": "Runtime directory.", "example": str(runtime_dir)},
            {"name": "APP_ENV_FILE", "value": "app_env.json", "description": "Config filename.", "example": "app_env.json"},
            {"name": "APP_ENV_PATH", "value": str(config_dir / "app_env.json"), "description": "Config path.", "example": str(config_dir / "app_env.json")},
        ],
    }


class EnvironmentTests(unittest.TestCase):
    def test_default_init_writes_local_links_central_and_quotes_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repository"
            resources = root / "resources"
            resources.mkdir(parents=True)
            system_home = Path(temporary) / "system home"
            template = document(system_home)
            template["variables"].append({
                "name": "QUOTED_VALUE",
                "value": "name with ' quote",
                "description": "Value used to exercise shell quoting.",
                "example": "plain value",
            })
            (resources / "app_env.template.json").write_text(json.dumps(template), encoding="utf-8")
            service = EnvironmentService(root)

            with patch("app.services.environment.os.geteuid", return_value=1000):
                result = service.initialize(use_default=True, file=None, interactive=False)

            local = resources / "app_env.json"
            central = system_home / "config" / "app_env.json"
            export = system_home / "config" / "environment.sh"
            self.assertTrue(local.is_file())
            self.assertTrue(central.is_symlink())
            self.assertEqual(central.resolve(), local.resolve())
            shell_integration = export.read_text(encoding="utf-8")
            self.assertIn("export QUOTED_VALUE='name with '\"'\"' quote'", shell_integration)
            self.assertIn("asystem_env_export()", shell_integration)
            self.assertIn("command /usr/local/bin/asystem_env_export", shell_integration)
            self.assertIsNone(result["profile"])

    def test_shell_integration_loads_exports_in_current_bash(self) -> None:
        values = {"EXAMPLE_VALUE": "available after command"}
        integration = EnvironmentService.render_shell_integration(values)

        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "environment.sh"
            script.write_text(integration, encoding="utf-8")
            completed = subprocess.run(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    f"source {shlex.quote(str(script))}; printf '%s' \"$EXAMPLE_VALUE\"",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "available after command")

    def test_unknown_and_cyclic_placeholders_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "resources").mkdir()
            service = EnvironmentService(root)
            invalid = document(root)
            invalid["variables"][0]["value"] = "${MISSING}"
            with self.assertRaisesRegex(ConfigurationError, "Nieznany placeholder"):
                service.validate(invalid)
            invalid["variables"][0]["value"] = "${USER_SYSTEM_HOME}"
            invalid["variables"][1]["value"] = "${USER_SYSTEM}"
            with self.assertRaisesRegex(ConfigurationError, "Cykl placeholderów"):
                service.validate(invalid)

    def test_central_path_cannot_escape_system_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "resources").mkdir()
            service = EnvironmentService(root)
            invalid = document(root / "home")
            next(item for item in invalid["variables"] if item["name"] == "APP_ENV_PATH")["value"] = "/etc/escape.json"
            with self.assertRaisesRegex(ConfigurationError, "APP_ENV_PATH"):
                service.validate(invalid)

    def test_default_lookup_does_not_fall_back_to_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repository"
            resources = root / "resources"
            resources.mkdir(parents=True)
            value = document(Path(temporary) / "system")
            encoded = json.dumps(value)
            (resources / "app_env.template.json").write_text(encoded, encoding="utf-8")
            (resources / "app_env.json").write_text(encoded, encoding="utf-8")
            service = EnvironmentService(root)

            self.assertEqual(service.get("USER_SYSTEM_HOME", local=True), str(Path(temporary) / "system"))
            with self.assertRaisesRegex(ConfigurationError, "Brak pliku konfiguracji"):
                service.get("USER_SYSTEM_HOME")

    def test_file_mode_persists_the_selected_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repository"
            (root / "resources").mkdir(parents=True)
            selected = base / "selected.json"
            value = document(base / "system")
            value["variables"][0]["value"] = "selected-user"
            selected.write_text(json.dumps(value), encoding="utf-8")
            service = EnvironmentService(root)

            with patch("app.services.environment.os.geteuid", return_value=1000):
                result = service.initialize(
                    use_default=False,
                    file=str(selected),
                    interactive=False,
                )

            self.assertEqual(result["source"], str(selected))
            self.assertEqual(service.get("USER_SYSTEM", local=True), "selected-user")

    def test_interactive_mode_uses_defaults_for_empty_answers(self) -> None:
        class TerminalInput(io.StringIO):
            def isatty(self) -> bool:
                return True

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repository"
            resources = root / "resources"
            resources.mkdir(parents=True)
            value = document(base / "system")
            (resources / "app_env.template.json").write_text(json.dumps(value), encoding="utf-8")
            service = EnvironmentService(root)
            answers = TerminalInput("\n" * len(value["variables"]))

            with patch("app.services.environment.os.geteuid", return_value=1000):
                service.initialize(
                    use_default=False,
                    file=None,
                    interactive=True,
                    input_stream=answers,
                    output_stream=io.StringIO(),
                )

            self.assertEqual(service.get("USER_SYSTEM", local=True), "tester")

    def test_env_init_requires_exactly_one_mode_before_execution(self) -> None:
        specs = Command.load_specs(APPLICATION_ROOT / "app" / "specs", {
            "AppAdd", "AppCall", "AppList", "AppRemove", "ConsoleDispatch", "EnvInit", "EnvExport", "GetVar",
            "Install", "Reinstall", "RuntimeStart", "RuntimeStatus", "RuntimeStop", "SystemStatus",
            "UserCreate", "UserGet", "UserList", "UserSet",
        })
        parser = Command(specs["env-init"])
        with self.assertRaisesRegex(Exception, "Wybierz"):
            parser.parse([])
        self.assertIsNone(parser.parse(["--help"]))
        request = parser.parse(["--default"])
        self.assertTrue(request.arguments["default"])

    def test_install_without_confirmation_has_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = InstallationService(root)
            result = service.install({"user": "test-user", "yes": False})
            self.assertEqual(result.exit_code, 2)
            self.assertEqual(list(root.iterdir()), [])

    def test_cli_renders_expected_error_without_traceback(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ENTRYPOINT), "env-init"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Błąd:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


    def test_command_parser_uses_environment_only_when_dev_policy_enables_it(self) -> None:
        spec = {
            "schema_version": 1,
            "command": "sample",
            "flags": [{
                "long": "--user", "takes_value": True, "type": "string",
                "env": "USER_SYSTEM", "var": "USER_SYSTEM",
            }],
        }
        shell_first = Command(
            spec, environment={"USER_SYSTEM": "shell-user"},
            variable_resolver=lambda _name: "json-user", environment_first=True,
        ).parse(["--user", "cli-user"])
        self.assertEqual(shell_first.arguments["user"], "shell-user")
        self.assertEqual(shell_first.sources["user"], "environment")

        cli_first = Command(
            spec, environment={"USER_SYSTEM": "shell-user"},
            variable_resolver=lambda _name: "json-user", environment_first=False,
        ).parse(["--user", "cli-user"])
        self.assertEqual(cli_first.arguments["user"], "cli-user")
        self.assertEqual(cli_first.sources["user"], "cli")

        json_fallback = Command(
            spec, environment={"USER_SYSTEM": "shell-user"},
            variable_resolver=lambda _name: "json-user", environment_first=False,
        ).parse([])
        self.assertEqual(json_fallback.arguments["user"], "json-user")
        self.assertEqual(json_fallback.sources["user"], "app_env")

    def test_application_environment_applies_mode_specific_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "app_env.json"
            dev = document(Path(temporary) / "home", mode="dev")
            configuration = ApplicationEnvironment(
                dev, source=source, environment={"USER_SYSTEM": "shell-user"}
            )
            self.assertEqual(
                configuration.select("USER_SYSTEM", flag="cli-user"), "shell-user"
            )

            next(item for item in dev["variables"] if item["name"] == "BASH_SOURCE")["value"] = "false"
            configuration = ApplicationEnvironment(
                dev, source=source, environment={"USER_SYSTEM": "shell-user"}
            )
            self.assertEqual(
                configuration.select("USER_SYSTEM", flag="cli-user"), "cli-user"
            )

            system = document(Path(temporary) / "home", mode="system")
            configuration = ApplicationEnvironment(
                system, source=source, environment={"USER_SYSTEM": "shell-user"}
            )
            self.assertEqual(
                configuration.select("USER_SYSTEM", flag="cli-user"), "cli-user"
            )
            self.assertEqual(configuration.select("USER_SYSTEM"), "tester")

    def test_system_discovery_prefers_app_env_path_and_keeps_local_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "resources"
            resources.mkdir()
            local = document(root / "home", mode="system")
            central_path = root / "central" / "app_env.json"
            next(item for item in local["variables"] if item["name"] == "APP_CONFIG_DIR")["value"] = str(central_path.parent)
            next(item for item in local["variables"] if item["name"] == "APP_ENV_PATH")["value"] = str(central_path)
            (resources / "app_env.json").write_text(json.dumps(local), encoding="utf-8")

            fallback = ApplicationEnvironment.discover(root)
            self.assertEqual(fallback.source, resources / "app_env.json")

            central = json.loads(json.dumps(local))
            next(item for item in central["variables"] if item["name"] == "USER_SYSTEM")["value"] = "central-user"
            central_path.parent.mkdir()
            central_path.write_text(json.dumps(central), encoding="utf-8")
            selected = ApplicationEnvironment.discover(root)
            self.assertEqual(selected.source, central_path)
            self.assertEqual(selected.select("USER_SYSTEM"), "central-user")

    def test_environment_activation_is_explicit_and_disabled_in_dev_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "resources"
            resources.mkdir()
            service = EnvironmentService(root)
            dev = document(root / "home", mode="dev")
            (resources / "app_env.json").write_text(json.dumps(dev), encoding="utf-8")
            with patch.dict("app.services.environment.os.environ", {}, clear=True):
                self.assertEqual(service.load_into_environment(optional=False), {})
                self.assertNotIn("USER_SYSTEM", os.environ)

            system = document(root / "home", mode="system")
            central = Path(next(item for item in system["variables"] if item["name"] == "APP_ENV_PATH")["value"] )
            central.parent.mkdir(parents=True)
            central.write_text(json.dumps(system), encoding="utf-8")
            (resources / "app_env.json").write_text(json.dumps(system), encoding="utf-8")
            with patch.dict("app.services.environment.os.environ", {}, clear=True):
                loaded = service.load_into_environment(optional=False)
                self.assertEqual(loaded["USER_SYSTEM"], "tester")
                self.assertEqual(os.environ["USER_SYSTEM"], "tester")
                self.assertNotIn("BASH_SOURCE", os.environ)


if __name__ == "__main__":
    unittest.main()
