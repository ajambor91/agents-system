"""Lifecycle mutations execute only in temporary trees with mocked systemd."""
from __future__ import annotations
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import pwd
import grp
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from install.src.parent import InstallerParent
from install.src.enums import InstallerMode
from install.src.installer import Installer, install_parser
from install.src.journal import InstallJournal
from install.src.reconfigure import Reconfigure
from install.src.reinstaller import Reinstaller
from install.src.uninstaller import Uninstaller
from install.src.errors import InstallationError
from install.src.shared import lifecycle_parser
from install.src.shared.lifecycle import read_environment
from install.src.rollback import InstallationRollback
from manifests import ManifestValidator
from manifests.app.helpers.manifests_validator import ManifestValidationStrategy


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.units = self.base / 'units'
        self.units.mkdir()
        self.calls = []
        self.fail_restart = False
        self.account = pwd.getpwuid(os.getuid())
        self.group = grp.getgrgid(os.getgid())
        self.installer = Installer(ROOT, environment={}, effective_uid=0, runner=self.runner, unit_root=self.units)
        config = self.installer.resolve(install_parser().parse_args([
            '--mode', 'system', '--system-user', self.account.pw_name,
            '--system-group', self.group.gr_name, '--target', str(self.base / 'application'),
            '--config-dir', str(self.base / 'config'), '--data-dir', str(self.base / 'data'),
            '--runtime-dir', str(self.base / 'run'),
        ]))
        self.config = replace(config, commands_dir=self.base / 'bin', user_home=Path(self.account.pw_dir))
        self.journals = []
        real_create = InstallJournal.create

        def create(*args):
            journal = real_create(*args)
            self.journals.append(journal)
            self.addCleanup(lambda: __import__('shutil').rmtree(journal.root, ignore_errors=True))
            return journal

        def open_journal(path):
            # Journals are owned by the test account; production open() retains
            # its root ownership checks. No real host paths are used here.
            for journal in self.journals:
                if journal.root == Path(path):
                    return InstallJournal(journal.root, json.loads(journal.path.read_text()))
            raise InstallationError('unknown test journal')

        self.create_patch = patch.object(InstallJournal, 'create', side_effect=create)
        self.open_patch = patch.object(InstallJournal, 'open', side_effect=open_journal)
        self.create_patch.start()
        self.open_patch.start()
        self.addCleanup(self.create_patch.stop)
        self.addCleanup(self.open_patch.stop)
        with patch.object(self.installer, '_prepare_account', return_value=(os.getuid(), os.getgid())):
            self.install_result = self.installer.install_configuration(self.config)
        self.journal = self.install_result['journal']

    def runner(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[0] in {'usermod', 'gpasswd', 'groupadd', 'groupdel', 'useradd', 'userdel'}:
            return subprocess.CompletedProcess(argv, 0, '', '')
        if argv[0] in {'systemctl', 'systemd-analyze'}:
            if argv[:3] == ['systemctl', 'enable', '--now']:
                pointer = self.config.install_dir / 'src/.env'
                self.assertTrue(pointer.is_file(), 'runtime must start after .env exists')
                self.assertEqual(pointer.read_text(), f'ABSOLUTE_CONFIG_PATH={self.config.config_dir / "app_env.json"}\n')
            if self.fail_restart and argv[:3] == ['systemctl', 'enable', '--now']:
                self.fail_restart = False
                return subprocess.CompletedProcess(argv, 1, '', 'injected restart failure')
            return subprocess.CompletedProcess(argv, 0, '', '')
        return subprocess.run(argv, **kwargs)

    def test_invoker_membership_is_added_after_verification(self):
        events = []
        config = replace(self.config, force=True)
        verify = self.installer._verify
        def verified(configuration):
            events.append('verify')
            return verify(configuration)
        def membership(configuration, journal, gid):
            events.append('membership')
            self.assertEqual(configuration.invoker.name, config.invoker.name)
            self.assertEqual(gid, self.group.gr_gid)
        with patch.object(self.installer, '_prepare_account', return_value=(os.getuid(), os.getgid())), patch.object(self.installer, '_verify', side_effect=verified), patch.object(self.installer, '_add_invoker_to_access_group', side_effect=membership):
            self.installer.install_configuration(config)
        self.assertEqual(events, ['verify', 'membership'])

    def arguments(self, mode, *extra):
        return lifecycle_parser(mode).parse_args(['--yes', '--journal', self.journal, *extra])

    def new_environment(self, **changes):
        document = json.loads((self.config.config_dir / 'app_env.json').read_text())
        for item in document['variables']:
            if item['name'] in changes:
                item['value'] = changes[item['name']]
        path = self.base / 'new configuration.json'
        path.write_text(json.dumps(document))
        return path

    def test_installed_wrappers_use_copied_help_and_require_confirmation(self):
        package = self.config.install_dir / 'src/install'
        self.assertEqual(Path(self.install_result['installer_module_dir']), package)
        self.assertTrue((package / '__main__.py').is_file())
        for operation, filename in [('uninstall', 'uninstaller.json'), ('reinstall', 'reinstaller.json'), ('reconfigure', 'reconfigure.json')]:
            wrapper = self.config.commands_dir / ('asystem-' + operation)
            self.assertTrue(wrapper.is_symlink())
            document_path = package / 'resources' / filename
            document = json.loads(document_path.read_text())
            document['description'] = 'Pomoc ze zainstalowanej paczki ' + operation
            document_path.write_text(json.dumps(document))
            result = subprocess.run([str(wrapper), '--help'], cwd=self.base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(document['description'], result.stdout)
            self.assertIn('--yes', result.stdout)
            args = [str(wrapper), '--journal', '/tmp/no-such-journal']
            if operation == 'reconfigure':
                args += ['--envs', '/tmp/no-such-environment']
            result = subprocess.run(args, cwd=self.base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Wymagana flaga --yes', result.stderr)

    def test_classes_follow_abstract_contract_and_modes(self):
        for cls in (Installer, Uninstaller, Reinstaller, Reconfigure):
            self.assertTrue(issubclass(cls, InstallerParent))
        self.assertEqual(InstallerMode.REINSTALL.value, 'reinstall')

    def test_reconfigure_updates_config_runtime_class_and_unit(self):
        path = self.new_environment(MAX_MESSAGE_BYTES_BASE='2048')
        data = self.config.data_dir / 'preserve.txt'
        data.write_text('saved')
        result = Reconfigure(installer=self.installer).execute(self.arguments(InstallerMode.RECONFIGURE, '--envs', str(path)))
        self.assertEqual(result['status'], 'reconfigured')
        values = {item['name']: item['value'] for item in read_environment(self.config.config_dir / 'app_env.json')['variables']}
        self.assertEqual(values['MAX_MESSAGE_BYTES_BASE'], '2048')
        self.assertEqual(data.read_text(), 'saved')
        self.assertTrue((self.config.install_dir / 'src/lib/configuration/configuration.py').is_file())
        self.assertIn(['systemctl', 'stop', 'agents-system.service'], self.calls)
        self.assertIn(['systemctl', 'enable', '--now', 'agents-system.service'], self.calls)

    def test_invalid_env_is_rejected_before_journal_or_service_access(self):
        path = self.new_environment(MAX_MESSAGE_BYTES_BASE='zero')
        before = len(self.calls)
        with patch.object(InstallJournal, 'open') as opened, patch.object(InstallJournal, 'create') as created:
            with self.assertRaisesRegex(InstallationError, 'positive integer'):
                Reconfigure(installer=self.installer).execute(self.arguments(InstallerMode.RECONFIGURE, '--envs', str(path)))
            opened.assert_not_called()
            created.assert_not_called()
        self.assertEqual(len(self.calls), before)

    def test_reconfigure_rejects_infrastructure_migration(self):
        path = self.new_environment(USER_SYSTEM='other-user')
        with self.assertRaisesRegex(InstallationError, 'USER_SYSTEM'):
            Reconfigure(installer=self.installer).execute(self.arguments(InstallerMode.RECONFIGURE, '--envs', str(path)))
        self.assertEqual(len(self.journals), 1)

    def test_failed_reconfigure_restores_files_and_service(self):
        old = (self.config.config_dir / 'app_env.json').read_bytes()
        source = self.config.install_dir / 'src/lib/configuration/configuration.py'
        source_before = source.read_bytes()
        path = self.new_environment(MAX_MESSAGE_BYTES_BASE='4096')
        self.fail_restart = True
        with self.assertRaisesRegex(InstallationError, 'injected restart failure'):
            Reconfigure(installer=self.installer).execute(self.arguments(InstallerMode.RECONFIGURE, '--envs', str(path)))
        self.assertEqual((self.config.config_dir / 'app_env.json').read_bytes(), old)
        self.assertEqual(source.read_bytes(), source_before)
        self.assertEqual(json.loads(self.journals[-1].path.read_text())['status'], 'rolled-back')
        self.assertIn(['systemctl', 'start', 'agents-system.service'], self.calls)

    def test_reinstall_preserves_configuration_and_data(self):
        data = self.config.data_dir / 'keep.txt'
        data.write_text('saved')
        environment = (self.config.config_dir / 'app_env.json').read_bytes()
        with patch.object(self.installer, '_prepare_account', return_value=(os.getuid(), os.getgid())):
            result = Reinstaller(installer=self.installer).execute(self.arguments(InstallerMode.REINSTALL))
        self.assertEqual(result['status'], 'reinstalled')
        self.assertEqual((self.config.config_dir / 'app_env.json').read_bytes(), environment)
        self.assertEqual(data.read_text(), 'saved')
        state = json.loads((Path(result['journal']) / 'journal.json').read_text())
        self.assertEqual(state['outputs']['status'], 'reinstalled')

    def test_uninstall_preserves_data_and_rollback_restores_app(self):
        data = self.config.data_dir / 'keep.txt'
        data.write_text('saved')
        result = Uninstaller(installer=self.installer).execute(self.arguments(InstallerMode.UNINSTALL))
        self.assertEqual(result['status'], 'uninstalled')
        self.assertFalse(self.config.install_dir.exists())
        self.assertFalse(self.config.config_dir.exists())
        self.assertFalse((self.units / 'agents-system.service').exists())
        self.assertFalse((self.config.commands_dir / 'asystem').exists())
        self.assertEqual(data.read_text(), 'saved')
        InstallationRollback(runner=self.runner, effective_uid=0).rollback(Path(result['journal']))
        self.assertTrue(self.config.install_dir.is_dir())
        self.assertTrue((self.config.commands_dir / 'asystem').is_symlink())
        self.assertTrue((self.config.config_dir / 'app_env.json').is_file())
        self.assertTrue((self.config.data_dir / 'installed_modules/agents-system.json').is_file())
        self.assertEqual(data.read_text(), 'saved')

    def test_explicit_purge_removes_only_marked_data(self):
        result = Uninstaller(installer=self.installer).execute(self.arguments(InstallerMode.UNINSTALL, '--purge-data'))
        self.assertFalse(result['data_preserved'])
        self.assertFalse(self.config.data_dir.exists())

    def test_foreign_command_is_rejected_before_mutations(self):
        command = self.config.commands_dir / 'asystem'
        command.unlink()
        command.write_text('foreign')
        with self.assertRaisesRegex(InstallationError, 'Obca'):
            Uninstaller(installer=self.installer).execute(self.arguments(InstallerMode.UNINSTALL))
        self.assertEqual(command.read_text(), 'foreign')
        self.assertEqual(len(self.journals), 1)

    def test_dev_reconfigure_and_uninstall_keep_the_checkout(self):
        checkout = self.base / 'checkout'
        checkout.mkdir()
        for directory in ('src', 'resources', 'internal_scripts', 'host_scripts', 'install'):
            shutil.copytree(ROOT / directory, checkout / directory,
                            ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build'))
        installer = Installer(checkout, environment={}, effective_uid=0, unit_root=self.units)
        arguments = install_parser().parse_args([
            '--yes', '--mode', 'dev', '--invoker', self.account.pw_name,
            '--target', str(self.base / 'dev-link'), '--config-dir', str(self.base / 'dev-config'),
            '--data-dir', str(self.base / 'dev-data'), '--runtime-dir', str(self.base / 'dev-run'),
            '--commands-dir', str(self.base / 'dev-bin'),
        ])
        configuration = installer.resolve(arguments)
        result = installer.execute(arguments)
        self.assertTrue(configuration.install_dir.is_symlink())
        # Resolving an existing managed symlink must retain its install identity.
        self.assertEqual(installer.resolve(arguments).install_dir, configuration.install_dir)
        document = read_environment(configuration.config_dir / 'app_env.json')
        for item in document['variables']:
            if item['name'] == 'MAX_MESSAGE_BYTES_BASE':
                item['value'] = '4096'
        envs = self.base / 'dev-new.json'
        envs.write_text(json.dumps(document))
        reconfigured = Reconfigure(installer=installer).execute(lifecycle_parser(InstallerMode.RECONFIGURE).parse_args([
            '--yes', '--journal', result['journal'], '--envs', str(envs),
        ]))
        self.assertEqual(reconfigured['status'], 'reconfigured')
        removed = Uninstaller(installer=installer).execute(lifecycle_parser(InstallerMode.UNINSTALL).parse_args([
            '--yes', '--journal', reconfigured['journal'],
        ]))
        self.assertEqual(removed['status'], 'uninstalled')
        self.assertTrue(checkout.is_dir())
        self.assertFalse(configuration.install_dir.is_symlink())
        self.assertFalse((checkout / 'src/.env').exists())
        self.assertTrue(configuration.data_dir.is_dir())
        InstallationRollback(effective_uid=0).rollback(Path(removed['journal']))
        self.assertTrue(configuration.install_dir.is_symlink())
        self.assertTrue((checkout / 'src/.env').is_file())

    def test_lifecycle_contracts_match_parser_flags(self):
        for mode in (InstallerMode.UNINSTALL, InstallerMode.REINSTALL, InstallerMode.RECONFIGURE, InstallerMode.ROLLBACK):
            from install.src.consts import HELP_MANIFEST_FILES
            contract = json.loads((ROOT / 'install/src/resources' / HELP_MANIFEST_FILES[mode.value]).read_text())
            expected = [option for action in lifecycle_parser(mode)._actions for option in action.option_strings]
            self.assertEqual(contract['flag_names'], expected)
            declared = [option for flag in contract['flags'] for option in (flag.get('short'), flag.get('long'), *flag.get('aliases', [])) if option]
            self.assertEqual(declared, expected)

    def test_reconfigure_wrapper_validates_spaced_env_path_before_journal(self):
        path = self.base / 'broken configuration.json'
        path.write_text('{broken')
        result = subprocess.run([
            'bash', str(ROOT / 'install/reconfigure.sh'), '--yes', '--journal', '/tmp/no-journal',
            '--envs', str(path),
        ], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Nie można odczytać konfiguracji', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_root_required_before_mutating_operations(self):
        installer = Installer(ROOT, effective_uid=1000)
        with self.assertRaisesRegex(InstallationError, 'root'):
            Uninstaller(installer=installer).execute(self.arguments(InstallerMode.UNINSTALL))
        with self.assertRaisesRegex(InstallationError, 'root'):
            Reinstaller(installer=installer).execute(self.arguments(InstallerMode.REINSTALL))


class StrategyTests(unittest.TestCase):
    def test_strategy_can_be_injected_without_changing_dispatch(self):
        from dataclasses import dataclass
        from manifests.app.models.manifest_abc import ManifestModel
        @dataclass(kw_only=True)
        class ExampleModel(ManifestModel):
            valid: bool
            def _validate_content(self):
                def check():
                    if not self.valid:
                        raise ValueError('invalid example')
                self._capture('valid', check)
        class ExampleStrategy(ManifestValidationStrategy):
            kind = 'example'
            def create_model(self, data):
                return ExampleModel(valid=data.get('valid', False))
        strategy = ExampleStrategy()
        self.assertTrue(ManifestValidator.validate({'kind': 'example', 'valid': True}, strategies=[strategy]))
        with self.assertRaisesRegex(ValueError, 'invalid example'):
            ManifestValidator.validate({'kind': 'example'}, strategies=[strategy])

    def test_environment_errors_are_aggregated(self):
        from manifests.app.exceptions import ManifestValidationError
        with self.assertRaises(ManifestValidationError) as caught:
            ManifestValidator.validate({'kind': 'agents-system-environment', 'schema_version': 2, 'variables': []})
        self.assertGreater(len(caught.exception.errors), 2)


if __name__ == '__main__':
    unittest.main()
