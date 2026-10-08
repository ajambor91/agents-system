"""Group access and unprivileged registry writes, using only temporary paths."""
import grp
import os
from pathlib import Path
import pwd
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from install.src.installer import Installer
from install.src.rollback import InstallationRollback
from agents_manager.app.services.state import AgentStateService


class InstallationPermissionsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.account = pwd.getpwuid(os.getuid())
        self.gid = os.getgid()
        self.installer = Installer(effective_uid=0, runner=Mock())

    def test_state_roots_are_group_writable_and_inherit_group(self):
        configuration = SimpleNamespace(data_dir=self.root/'data', runtime_dir=self.root/'run')
        self.installer._write_marker = Mock(side_effect=lambda root, configuration: (root/'.agents-system-install.json').write_text('{}'))
        self.installer._prepare_state_directories(configuration, Mock(), os.getuid(), self.gid)
        for path in (configuration.data_dir, configuration.runtime_dir):
            self.assertEqual(path.stat().st_mode & 0o7777, 0o2770)
            self.assertEqual(path.stat().st_gid, self.gid)

    def test_existing_state_permission_change_can_be_rolled_back(self):
        path = self.root/'data'
        path.mkdir(mode=0o750)
        configuration = SimpleNamespace(data_dir=path, runtime_dir=self.root/'run')
        journal = Mock()
        self.installer._write_marker = Mock(side_effect=lambda root, configuration: (root/'.agents-system-install.json').write_text('{}'))
        self.installer._prepare_state_directories(configuration, journal, os.getuid(), self.gid)
        mutation = journal.prepare.call_args_list[0].kwargs
        self.assertEqual(mutation['mode'], 0o750)
        with patch.object(InstallationRollback, '_validated_path', return_value=path):
            InstallationRollback()._reverse(journal, {'kind':'path_permissions', **mutation})
        self.assertEqual(path.stat().st_mode & 0o7777, 0o750)

    def test_all_application_files_have_group_access(self):
        plain, executable = self.root/'data.json', self.root/'command.sh'
        plain.write_text('{}')
        executable.write_text('#!/bin/bash\n')
        executable.chmod(0o700)
        self.installer._set_ownership(self.root, os.getuid(), self.gid, 'system')
        self.assertEqual(self.root.stat().st_mode & 0o7777, 0o2770)
        self.assertEqual(plain.stat().st_mode & 0o777, 0o660)
        self.assertEqual(executable.stat().st_mode & 0o777, 0o770)

    def test_invoker_added_to_user_system_group_once_and_journaled(self):
        configuration = SimpleNamespace(invoker=SimpleNamespace(name='caller', gid=123), user_system='selected-user')
        self.installer._run = Mock()
        journal = Mock()
        with patch('install.src.installer.os.getgrouplist', return_value=[123]):
            self.installer._add_invoker_to_access_group(configuration, journal, 456)
        self.installer._run.assert_called_once_with(['usermod','-a','-G','selected-user','caller'])
        journal.prepare.assert_called_once_with('added_membership', user='caller', group='selected-user')
        journal.applied.assert_called_once_with(journal.prepare.return_value)
        self.installer._run.reset_mock()
        with patch('install.src.installer.os.getgrouplist', return_value=[123,456]):
            self.installer._add_invoker_to_access_group(configuration, journal, 456)
        self.installer._run.assert_not_called()

    def test_registry_write_is_atomic_and_never_calls_sudo(self):
        runner = Mock()
        context = SimpleNamespace(state_root=self.root, state_owner=self.account.pw_name)
        state = AgentStateService(context, runner)
        target = self.root/'agents.json'
        target.write_text('{"old":true}')
        state.write_json(target, {'agents':{}})
        self.assertIn('"agents": {}', target.read_text())
        self.assertEqual(target.stat().st_mode & 0o777, 0o660)
        self.assertEqual(target.stat().st_gid, self.gid)
        runner.run_privileged.assert_not_called()
        self.assertEqual(list(self.root.glob('.agents.json.*')), [])

    def test_failed_registry_replace_preserves_previous_document(self):
        state = AgentStateService(SimpleNamespace(state_root=self.root, state_owner=self.account.pw_name), Mock())
        target = self.root/'agents.json'
        target.write_text('previous')
        with patch('agents_manager.app.services.state.os.replace', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                state.write_json(target, {})
        self.assertEqual(target.read_text(), 'previous')
        self.assertEqual(list(self.root.glob('.agents.json.*')), [])

    def test_missing_state_root_is_reported_without_creation_or_sudo(self):
        runner = Mock()
        root = self.root/'missing'
        state = AgentStateService(SimpleNamespace(state_root=root), runner)
        with self.assertRaises(FileNotFoundError):
            state.prepare_root()
        self.assertFalse(root.exists())
        runner.run_privileged.assert_not_called()

    def test_agent_reader_gets_traversal_of_private_state_root(self):
        runner = Mock()
        context = SimpleNamespace(state_root=self.root, state_owner='system-user', state_owner_home=self.root/'home')
        state = AgentStateService(context, runner)
        with patch('agents_manager.app.services.state.shutil.which', return_value='/usr/bin/setfacl'):
            state._grant_file_reader('agent-user', self.root/'runtime.json', dry_run=False)
        runner.run_privileged.assert_any_call(['setfacl', '-m', 'u:agent-user:--x', str(self.root)])
