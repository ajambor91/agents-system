"""Contract tests for the standalone install application."""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from install.src.errors import InstallationError  # noqa: E402
from install.src.installer import Installer, install_parser  # noqa: E402
from install.src.rollback import InstallationRollback  # noqa: E402


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.account = pwd.getpwuid(os.getuid())
        self.group = grp.getgrgid(self.account.pw_gid)

    def arguments(self, *extra: str) -> argparse.Namespace:
        return install_parser().parse_args(["--mode", "dev", "--invoker", self.account.pw_name, *extra])

    def test_mode_defaults_to_system_and_user_system_requires_value(self) -> None:
        self.assertEqual(install_parser().parse_args([]).mode, "system")
        with self.assertRaises(SystemExit):
            self.arguments("--user-system")

    def test_dev_without_clone_uses_invoker_and_copies_nothing(self) -> None:
        configuration = Installer(ROOT, environment={}, effective_uid=0).resolve(self.arguments())
        self.assertEqual(configuration.user_system, self.account.pw_name)
        self.assertEqual(configuration.user_group, self.group.gr_name)
        self.assertEqual(configuration.user_home, Path(self.account.pw_dir))
        self.assertEqual(
            configuration.install_dir, Path("/opt/agents-system")
        )
        self.assertFalse(configuration.dedicated_user)
        self.assertFalse(configuration.clone_repo)

    def test_dev_account_overrides_require_clone_repo(self) -> None:
        with self.assertRaisesRegex(InstallationError, "--user-group"):
            Installer(ROOT, environment={}, effective_uid=0).resolve(
                self.arguments("--user-group", self.group.gr_name)
            )

    def test_custom_paths_and_bash_policy_override_defaults(self) -> None:
        configuration = Installer(ROOT, environment={}, effective_uid=0).resolve(
            self.arguments(
                "--target", "/tmp/custom-agents-system",
                "--config-dir", "~/.${APP_NAME}/config",
                "--data-dir", "/dupa/chuj/codex/to/idiota",
                "--runtime-dir", "/tmp/custom-agents-runtime",
                "--bash-source", "false",
            )
        )
        self.assertEqual(configuration.install_dir, Path("/tmp/custom-agents-system"))
        self.assertEqual(
            configuration.config_dir, Path(self.account.pw_dir) / ".agents-system" / "config"
        )
        self.assertEqual(configuration.data_dir, Path("/dupa/chuj/codex/to/idiota"))
        self.assertEqual(configuration.runtime_dir, Path("/tmp/custom-agents-runtime"))
        self.assertEqual(configuration.bash_source, "false")

    def test_install_defaults_fall_back_to_install_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "package"
            (package / "install").mkdir(parents=True)
            shutil.copy2(ROOT / "install" / "default_install.json", package / "install")
            installer = Installer(package, environment={}, effective_uid=0)
            with patch.object(installer, "_validate_sources"):
                configuration = installer.resolve(self.arguments())
            self.assertEqual(configuration.install_dir, Path("/opt/agents-system"))

    def test_dev_without_clone_installs_only_a_symlink(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=0)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "linked-install"
            configuration = installer.resolve(
                self.arguments("--target", str(target))
            )
            journal = MagicMock()
            journal.prepare.return_value = 0
            installer._install_payload(configuration, journal)
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), ROOT.resolve())
            journal.applied.assert_called_once_with(0)

    def test_dev_clone_targets_only_user_system_home(self) -> None:
        configuration = Installer(ROOT, environment={}, effective_uid=0).resolve(
            self.arguments("--clone-repo")
        )
        self.assertTrue(configuration.clone_repo)
        self.assertTrue(configuration.dedicated_user)
        self.assertEqual(configuration.user_system, "user-system")
        self.assertEqual(
            configuration.install_dir, Path("/home/user-system/agents-system")
        )
        self.assertNotEqual(configuration.install_dir.parent, Path(self.account.pw_dir))

    def test_system_mode_uses_contract_paths(self) -> None:
        arguments = install_parser().parse_args(
            ["--mode", "system", "--invoker", self.account.pw_name]
        )
        configuration = Installer(ROOT, environment={}, effective_uid=0).resolve(arguments)
        self.assertEqual(configuration.user_system, "user-system")
        self.assertEqual(configuration.install_dir, Path("/opt/agents-system"))
        self.assertEqual(configuration.user_home, Path("/home/user-system"))
        self.assertEqual(configuration.config_dir, Path("/etc/agents-system"))
        self.assertEqual(configuration.data_dir, Path("/var/lib/agents-system"))
        self.assertEqual(configuration.runtime_dir, Path("/run/agents-system"))

    def test_non_root_stops_before_journal_creation(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=1000)
        with patch("install.src.installer.InstallJournal.create") as create:
            with self.assertRaisesRegex(InstallationError, "root"):
                installer.execute(self.arguments())
            create.assert_not_called()

    def test_force_refuses_foreign_installation(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=0)
        configuration = installer.resolve(self.arguments("--force"))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            foreign = base / "foreign"
            foreign.mkdir()
            configuration = replace(
                configuration,
                install_dir=foreign,
                config_dir=base / "config",
                commands_dir=base / "bin",
            )
            with self.assertRaisesRegex(InstallationError, "obcego celu dev"):
                installer._preflight(configuration)

    def test_dev_resources_are_rendered_and_linked(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=0)
        configuration = installer.resolve(self.arguments())
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "installed"
            (target / "resources").mkdir(parents=True)
            for module_name in (
                "agents-manager",
                "agents-data",
                "agents-data-backend",
                "agents-system",
                "app_api",
                "agents-data-runtime",
                "_runtime",
            ):
                (target / "src" / module_name).mkdir(parents=True)
            configuration = replace(
                configuration,
                install_dir=target,
                config_dir=Path(temporary) / "config",
                user_system=self.account.pw_name,
                user_group=self.group.gr_name,
                user_home=Path(self.account.pw_dir),
            )
            journal = MagicMock()
            journal.root = Path(temporary) / "journal"
            journal.prepare.return_value = 0
            installer._render_resources(configuration, journal)
            for name in ("app_env.json", "agents-system.module.json"):
                rendered = target / "resources" / name
                linked = target / "src" / "resources" / name
                self.assertTrue(rendered.is_file())
                self.assertTrue(linked.is_symlink())
                self.assertEqual(linked.resolve(), rendered.resolve())
                json.loads(rendered.read_text(encoding="utf-8"))

    def test_configuration_is_generated_from_published_app_env(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=0)
        configuration = installer.resolve(self.arguments())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "installed"
            config = base / "config"
            (target / "internal_scripts").mkdir(parents=True)
            (target / "src" / "internal_scripts").mkdir(parents=True)
            config.mkdir()
            shutil.copy2(
                ROOT / "internal_scripts" / "generate_configuration.sh",
                target / "internal_scripts" / "generate_configuration.sh",
            )
            shutil.copy2(
                ROOT / "src" / "internal_scripts" / "generate_configuration.py",
                target / "src" / "internal_scripts" / "generate_configuration.py",
            )
            app_env_path = config / "app_env.json"
            app_env_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "kind": "agents-system-environment",
                    "variables": [
                        {"name": "APP_DIR", "value": str(target)},
                        {"name": "MODULES_MANIFEST_FILE", "value": "agents-system.module.json"},
                    ],
                }),
                encoding="utf-8",
            )
            configuration = replace(
                configuration, install_dir=target, config_dir=config
            )
            journal = MagicMock()
            journal.prepare.return_value = 0

            generated = installer._generate_configuration(configuration, journal)

            self.assertEqual(
                generated,
                target / "src" / "lib" / "configuration" / "configuration.py",
            )
            content = generated.read_text(encoding="utf-8")
            self.assertIn("APP_DIR: ClassVar[str]", content)
            self.assertIn("MODULES_MANIFEST_FILE: ClassVar[str]", content)
            journal.applied.assert_called_once_with(0)

    def test_source_env_is_the_final_mutation_and_contains_only_config_path(self) -> None:
        installer = Installer(ROOT, environment={}, effective_uid=0)
        configuration = installer.resolve(self.arguments())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "installed"
            config = base / "config"
            (target / "src").mkdir(parents=True)
            config.mkdir()
            configuration = replace(
                configuration,
                install_dir=target,
                config_dir=config,
                user_system=self.account.pw_name,
                user_group=self.group.gr_name,
                user_home=Path(self.account.pw_dir),
            )
            app_env_path = config / "app_env.json"
            app_env_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "kind": "agents-system-environment",
                    "variables": [
                        {
                            "name": "APP_ENV_PATH",
                            "value": str(app_env_path),
                            "description": "Active config.",
                            "example": str(app_env_path),
                        }
                    ],
                }),
                encoding="utf-8",
            )
            journal = MagicMock()
            journal.prepare.return_value = 0
            with patch("install.src.installer.os.chown"):
                result = installer._write_absolute_config_pointer(
                    configuration,
                    journal,
                    owner_id=self.account.pw_uid,
                    group_id=self.group.gr_gid,
                )

            expected = target / "src" / ".env"
            self.assertEqual(result, expected)
            self.assertEqual(
                expected.read_text(encoding="utf-8"),
                f"ABSOLUTE_CONFIG_PATH={app_env_path}\n",
            )
            self.assertEqual(expected.stat().st_mode & 0o777, 0o640)
            journal.applied.assert_called_once_with(0)

            rollback_journal = SimpleNamespace(
                state={"configuration": configuration.public_dict()}
            )
            self.assertEqual(
                InstallationRollback._validated_path(rollback_journal, str(expected)),
                expected,
            )

        source = (ROOT / "install" / "src" / "installer.py").read_text(
            encoding="utf-8"
        )
        execute = source[
            source.index("    def execute("):source.index("    def _log(")
        ]
        self.assertLess(
            execute.index("self._render_resources("),
            execute.index("self._generate_configuration("),
        )
        self.assertLess(
            execute.index("self._generate_configuration("),
            execute.index("self._install_unit("),
        )
        self.assertLess(
            execute.index("self._install_unit("),
            execute.index("self._write_absolute_config_pointer("),
        )
        self.assertLess(
            execute.index("self._write_absolute_config_pointer("),
            execute.index("outputs = self._verify("),
        )

    def test_install_api_matches_contract_flags(self) -> None:
        contract = json.loads((ROOT / "install" / "install.json").read_text(encoding="utf-8"))
        api = json.loads((ROOT / "install" / "install.api.json").read_text(encoding="utf-8"))
        expected = [(item["short"], item["long"]) for item in contract["flags"]]
        actual = [(item["short"], item["long"]) for item in api["flags"]]
        self.assertEqual(actual, expected)
        expected_names = [
            flag
            for item in api["flags"]
            for flag in (item.get("short"), item.get("long"), *item.get("aliases", []))
            if flag
        ]
        self.assertEqual(api["flag_names"], expected_names)
        step_ids = [item["id"] for item in contract["steps"]]
        self.assertLess(
            step_ids.index("render-resources"),
            step_ids.index("generate-configuration"),
        )
        self.assertLess(
            step_ids.index("generate-configuration"),
            step_ids.index("install-service"),
        )
        self.assertLess(
            step_ids.index("install-service"),
            step_ids.index("write-source-env"),
        )
        self.assertLess(
            step_ids.index("write-source-env"),
            step_ids.index("verify"),
        )
        self.assertIn("source_env_pointer", contract["outputs"])

    def test_system_unit_template_renders_to_valid_unit(self) -> None:
        template = (ROOT / "resources" / "system.template.service").read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for directory in (base / "config", base / "data", base / "runtime"):
                directory.mkdir()
            values = {
                "INSTALL_MODE": "system",
                "APP_NAME": "agents-system",
                "APP_DIR": str(ROOT),
                "USER_SYSTEM": self.account.pw_name,
                "USER_GROUP": self.group.gr_name,
                "USER_SYSTEM_HOME": self.account.pw_dir,
                "APP_CONFIG_DIR": str(base / "config"),
                "APP_DATA_DIR": str(base / "data"),
                "APP_RUNTIME_DIR": str(base / "runtime"),
                "APP_RUNTIME_PATH": str(base / "runtime" / "main.sock"),
                "APP_ENV_PATH": str(base / "config" / "app_env.json"),
                "MODULES_MANIFEST_PATH": str(base / "config" / "agents-system.module.json"),
                "PYTHON_BIN": sys.executable,
            }
            for name, value in values.items():
                template = template.replace("{{" + name + "}}", value)
            self.assertNotIn("{{", template)
            unit = base / "agents-system.service"
            unit.write_text(template, encoding="utf-8")
            verified = subprocess.run(
                ["systemd-analyze", "verify", str(unit)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("APP_RUNTIME_PATH", template)
            self.assertNotIn("AGENTS_SYSTEM_HOME", template)
            self.assertNotIn("AGENTS_REPOSITORY_STATE_HOME", template)

    def test_wrappers_expose_help_and_errors_have_no_traceback(self) -> None:
        for wrapper in ("install.sh", "rollback.sh"):
            help_result = subprocess.run(
                ["bash", str(ROOT / "self" / wrapper), "--help"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
        result = subprocess.run(
            [sys.executable, str(ROOT / "install" / "main.py"), "--mode", "dev", "--invoker", "definitely-not-existing"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Błąd:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
