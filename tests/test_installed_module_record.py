"""Journaled installer copy to the rendered INSTALLED_MODULES_DIR."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install.src.errors import InstallationError
from install.src.installer import Installer, install_parser
from install.src.journal import InstallJournal
from install.src.rollback import InstallationRollback
import pwd


class InstalledModuleRecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.installer = Installer(ROOT, environment={}, effective_uid=0)
        arguments = install_parser().parse_args(["--mode", "dev", "--invoker", pwd.getpwuid(os.getuid()).pw_name])
        self.configuration = replace(self.installer.resolve(arguments),
            config_dir=self.base / "config", install_dir=self.base / "application",
            data_dir=self.base / "data", runtime_dir=self.base / "run")
        self.configuration.config_dir.mkdir()
        self.directory = self.base / "custom-data" / "nested" / "installed-modules"
        self.write_environment(str(self.directory))
        journal_root = self.base / "journal"
        journal_root.mkdir()
        (journal_root / "backups").mkdir()
        self.journal = InstallJournal(journal_root, {"configuration": self.configuration.public_dict(), "mutations": []})

    def write_environment(self, value):
        (self.configuration.config_dir / "app_env.json").write_text(json.dumps({"variables": [{"name": "INSTALLED_MODULES_DIR", "value": value}]}))

    def install(self, configuration=None):
        return self.installer._install_module_record(configuration or self.configuration, self.journal, os.getuid(), os.getgid())

    def rollback(self):
        rollback = InstallationRollback(effective_uid=0)
        for mutation in reversed(self.journal.state["mutations"]):
            rollback._reverse(self.journal, mutation)

    def test_copy_uses_rendered_path_preserves_bytes_and_is_reversible(self):
        target = self.install()
        self.assertEqual(target, self.directory / "agents-system.json")
        self.assertEqual(target.read_bytes(), (ROOT / "resources/agents-system.json").read_bytes())
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(target.stat().st_uid, os.getuid())
        self.assertFalse(self.configuration.data_dir.exists())
        self.rollback()
        self.assertFalse((self.base / "custom-data").exists())

    def test_force_replacement_restores_previous_record_and_preserves_other_files(self):
        self.directory.mkdir(parents=True)
        target = self.directory / "agents-system.json"
        target.write_text('previous document')
        other = self.directory / "plugin.json"
        other.write_text('plugin record')
        with self.assertRaisesRegex(InstallationError, "--force"):
            self.install()
        self.install(replace(self.configuration, force=True))
        self.rollback()
        self.assertEqual(target.read_text(), 'previous document')
        self.assertEqual(other.read_text(), 'plugin record')

    def test_symlink_directory_and_file_are_rejected(self):
        actual = self.base / "actual"
        actual.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(actual, target_is_directory=True)
        self.write_environment(str(linked / "modules"))
        with self.assertRaises(InstallationError):
            self.install()
        self.directory.mkdir(parents=True)
        (self.directory / "agents-system.json").symlink_to(actual / "foreign.json")
        self.write_environment(str(self.directory))
        with self.assertRaises(InstallationError):
            self.install(replace(self.configuration, force=True))
        self.assertFalse((actual / "foreign.json").exists())

    def test_invalid_configured_paths_fail_before_mutations(self):
        for value in ("relative", str(self.base / ".." / "escape"), None, ""):
            self.write_environment(value)
            with self.assertRaises(InstallationError):
                self.install()
        self.assertEqual(self.journal.state["mutations"], [])
