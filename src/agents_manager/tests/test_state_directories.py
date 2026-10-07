"""Per-agent state directories use the prepared shared group without sudo."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from agents_manager.app.services import state as state_module
from agents_manager.app.services.state import AgentStateService


class StateDirectoriesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state_root = self.root / "state"
        self.state_root.mkdir(mode=0o2770)
        self.state_root.chmod(0o2770)
        self.context = SimpleNamespace(state_root=self.state_root, state_owner="system-user")
        self.runner = Mock()
        self.service = AgentStateService(self.context, self.runner)

    def test_create_group_writable_directories_even_with_restrictive_umask(self):
        previous_umask = os.umask(0o077)
        try:
            paths = self.service.prepare("example")
        finally:
            os.umask(previous_umask)
        for directory in (paths.agent_dir, paths.shells_dir):
            metadata = directory.stat()
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o2770)
            self.assertEqual(metadata.st_gid, self.state_root.stat().st_gid)
        self.runner.run_privileged.assert_not_called()
        self.runner.run.assert_not_called()

    def test_existing_same_owner_directories_are_normalized_idempotently(self):
        agent = self.state_root / "example"
        shells = agent / "shells"
        shells.mkdir(parents=True)
        agent.chmod(0o700)
        shells.chmod(0o755)
        self.service.prepare("example")
        self.assertEqual(stat.S_IMODE(agent.stat().st_mode), 0o2770)
        self.assertEqual(stat.S_IMODE(shells.stat().st_mode), 0o2770)
        with patch.object(state_module.os, "fchown") as chown, patch.object(state_module.os, "fchmod") as chmod:
            self.service.prepare("example")
        chown.assert_not_called()
        chmod.assert_not_called()
        self.runner.run_privileged.assert_not_called()

    def test_valid_shared_directories_of_another_owner_need_no_ownership_operations(self):
        shells = self.state_root / "example" / "shells"
        shells.mkdir(parents=True)
        for directory in (shells.parent, shells):
            directory.chmod(0o2770)
        original_fstat = os.fstat

        def other_owner_metadata(fd):
            metadata = original_fstat(fd)
            values = list(metadata)
            values[4] = os.geteuid() + 1
            return os.stat_result(values)

        with patch.object(state_module.os, "fstat", side_effect=other_owner_metadata), \
                patch.object(state_module.os, "fchown", side_effect=AssertionError("must not change ownership")), \
                patch.object(state_module.os, "fchmod", side_effect=AssertionError("must not change mode")):
            self.service.prepare("example")
        self.runner.run_privileged.assert_not_called()

    def test_changing_group_also_restores_setgid_mode(self):
        parent_fd = os.open(self.state_root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, parent_fd)
        group_id = self.state_root.stat().st_gid
        metadata = SimpleNamespace(st_gid=group_id + 1, st_mode=stat.S_IFDIR | 0o2770)
        with patch.object(state_module.os, "fstat", return_value=metadata), \
                patch.object(state_module.os, "fchown") as chown, \
                patch.object(state_module.os, "fchmod") as chmod:
            directory_fd = self.service._prepare_directory("example", parent_fd, group_id)
        try:
            chown.assert_called_once_with(directory_fd, -1, group_id)
            chmod.assert_called_once_with(directory_fd, 0o2770)
        finally:
            os.close(directory_fd)

    def test_invalid_names_are_rejected_before_any_mutation(self):
        for name in ("../outside", "/absolute", "two/components", "..", ".", "", None):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.service.prepare(name)
        self.assertEqual(list(self.state_root.iterdir()), [])
        self.runner.run_privileged.assert_not_called()

    def test_existing_files_are_rejected_before_normalizing_agent_directory(self):
        agent = self.state_root / "example"
        agent.mkdir(mode=0o700)
        agent.chmod(0o700)
        (agent / "shells").write_text("keep this file")
        with self.assertRaises(ValueError):
            self.service.prepare("example")
        self.assertEqual(stat.S_IMODE(agent.stat().st_mode), 0o700)
        self.assertEqual((agent / "shells").read_text(), "keep this file")
        (self.state_root / "other").write_text("keep this agent file")
        with self.assertRaises(ValueError):
            self.service.prepare("other")
        self.assertEqual((self.state_root / "other").read_text(), "keep this agent file")

    def test_symlinks_and_broken_symlinks_are_rejected_without_following_them(self):
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        outside.chmod(0o700)
        (self.state_root / "example").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.service.prepare("example")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o700)
        agent = self.state_root / "other"
        agent.mkdir(mode=0o700)
        agent.chmod(0o700)
        (agent / "shells").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.service.prepare("other")
        self.assertEqual(stat.S_IMODE(agent.stat().st_mode), 0o700)
        (self.state_root / "broken").symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            self.service.prepare("broken")

    def test_dry_run_reports_without_creating_or_changing_directories(self):
        paths = self.service.prepare("example", dry_run=True)
        self.assertFalse(paths.agent_dir.exists())
        self.assertEqual(self.runner.report.call_count, 2)
        self.runner.run_privileged.assert_not_called()
        paths.agent_dir.mkdir()
        paths.agent_dir.chmod(0o700)
        self.service.prepare("example", dry_run=True)
        self.assertEqual(stat.S_IMODE(paths.agent_dir.stat().st_mode), 0o700)
        self.assertFalse(paths.shells_dir.exists())

    def test_missing_or_symlink_root_still_requires_installer(self):
        self.context.state_root = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            self.service.prepare("example")
        self.assertFalse(self.context.state_root.exists())
        root_link = self.root / "root-link"
        root_link.symlink_to(self.state_root, target_is_directory=True)
        self.context.state_root = root_link
        with self.assertRaises(FileNotFoundError):
            self.service.prepare("example")
        self.assertEqual(list(self.state_root.iterdir()), [])
        self.runner.run_privileged.assert_not_called()


class StateReaderTraversalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state_root = self.root / "state"
        self.state_root.mkdir(mode=0o2770)
        self.state_root.chmod(0o2770)
        self.owner_home = self.root / "home"
        self.owner_home.mkdir(mode=0o700)
        self.runner = Mock()
        self.service = AgentStateService(SimpleNamespace(
            state_root=self.state_root, state_owner="system-user", state_owner_home=self.owner_home,
        ), self.runner)
        self.paths = self.service.prepare("example")
        for file_path in (self.paths.config_json, self.paths.runtime_json, self.paths.agentrc, self.paths.bashrc):
            file_path.write_text("example")
            file_path.chmod(0o660)
        acl_available = patch.object(state_module.shutil, "which", return_value="/usr/bin/setfacl")
        acl_available.start()
        self.addCleanup(acl_available.stop)

    def expected_calls(self, file_path):
        directories = [self.owner_home, self.state_root, self.paths.agent_dir]
        if file_path.parent == self.paths.shells_dir:
            directories.append(self.paths.shells_dir)
        return [call(["setfacl", "-m", "u:agent-user:--x", str(directory)]) for directory in directories] + [
            call(["setfacl", "-m", "u:agent-user:r--", str(file_path)]),
        ]

    def test_config_and_runtime_readers_can_traverse_agent_directory(self):
        for method, file_path in ((self.service.grant_config_reader, self.paths.config_json),
                                  (self.service.grant_runtime_reader, self.paths.runtime_json)):
            with self.subTest(file=file_path.name):
                self.runner.reset_mock()
                method("agent-user", self.paths)
                self.assertEqual(self.runner.run_privileged.call_args_list, self.expected_calls(file_path))
        self.assertEqual(stat.S_IMODE(self.paths.agent_dir.stat().st_mode), 0o2770)
        self.assertEqual(stat.S_IMODE(self.state_root.stat().st_mode), 0o2770)

    def test_shell_reader_can_traverse_agent_and_shell_directories(self):
        self.service.grant_shell_reader("agent-user", self.paths)
        expected = self.expected_calls(self.paths.agentrc) + self.expected_calls(self.paths.bashrc)
        self.assertEqual(self.runner.run_privileged.call_args_list, expected)
        for directory in (self.state_root, self.paths.agent_dir, self.paths.shells_dir):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o2770)
        # Directory ACLs grant traversal only; shared inventories remain private.
        for recorded_call in self.runner.run_privileged.call_args_list:
            arguments = recorded_call.args[0]
            if arguments[-1] in {str(self.state_root), str(self.paths.agent_dir), str(self.paths.shells_dir)}:
                self.assertEqual(arguments[2], "u:agent-user:--x")

    def test_outside_or_symlink_paths_are_rejected_before_acl_changes(self):
        outside = self.root / "outside.json"
        outside.write_text("private")
        linked = self.paths.agent_dir / "linked.json"
        linked.symlink_to(outside)
        linked_directory = self.state_root / "linked-dir"
        linked_directory.symlink_to(self.paths.agent_dir, target_is_directory=True)
        candidates = (
            outside, linked, self.state_root / ".." / "outside.json",
            linked_directory / "config.json", self.paths.agent_dir,
        )
        for candidate in candidates:
            with self.subTest(path=candidate):
                with self.assertRaises(ValueError):
                    self.service._grant_file_reader("agent-user", candidate, dry_run=False)
        self.runner.run_privileged.assert_not_called()

    def test_owner_and_dry_run_do_not_execute_acl_commands(self):
        self.service.grant_runtime_reader("system-user", self.paths)
        self.service.grant_shell_reader("agent-user", self.paths, dry_run=True)
        self.runner.run_privileged.assert_not_called()
        self.assertEqual(self.runner.report.call_count, 2)


if __name__ == "__main__":
    unittest.main()
