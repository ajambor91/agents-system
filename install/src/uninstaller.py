"""Remove proven installation artifacts, retaining data and accounts by default."""
from __future__ import annotations
import argparse
import json
import hashlib
from pathlib import Path
from typing import Any

from .parent import InstallerParent
from .enums import InstallerMode
from .consts import ENVIRONMENT_FILE, INSTALLER_MODULE_NAME
from .errors import InstallationError
from .installer import Installer
from .journal import InstallJournal
from .shared.lifecycle import (
    validate_dev_runtime_stopped,
    configuration_from_journal, lifecycle_journal_configuration, managed_commands,
    read_environment, require_root, safe_managed_path, transaction,
    validate_environment_identity, validate_owned_installation, validate_managed_unit, validate_owned_directory,
)
from .shared.operations import delete_path


class Uninstaller(InstallerParent):
    operation = InstallerMode.UNINSTALL

    def __init__(self, *, installer: Installer | None = None, **installer_options: Any) -> None:
        self.installer = installer or Installer(**installer_options)

    def execute(self, arguments: argparse.Namespace) -> dict[str, Any]:
        self.require_yes(arguments)
        require_root(self.installer.effective_uid)
        previous = InstallJournal.open(Path(arguments.journal))
        if previous.state.get('status') == 'success' and previous.state.get('outputs', {}).get('status') == 'uninstalled':
            return {'status': 'already-uninstalled', 'journal': str(previous.root)}
        configuration = configuration_from_journal(previous, verbose=arguments.verbose, require_source=False)
        validate_owned_installation(configuration)
        document = read_environment(configuration.config_dir / ENVIRONMENT_FILE)
        validate_environment_identity(document, configuration)
        validate_dev_runtime_stopped(document, configuration)
        commands = managed_commands(previous, configuration)
        self.installer.verbose = configuration.verbose
        unit = self.installer.unit_root / f'{configuration.app_name}.service'
        if configuration.mode == 'system':
            validate_managed_unit(unit, configuration)
        env = configuration.install_dir / 'src/.env'
        expected = f"ABSOLUTE_CONFIG_PATH={configuration.config_dir / ENVIRONMENT_FILE}\n"
        if env.is_symlink() or not env.is_file() or env.read_text(encoding='utf-8') != expected:
            raise InstallationError(f"Obcy wskaźnik konfiguracji: {env}")
        record_raw = previous.state['configuration'].get('installed_modules_file')
        record = None
        if record_raw:
            record = safe_managed_path(record_raw, 'installed_modules_file')
            values = {item['name']: item['value'] for item in document['variables']}
            expected_record = Path(values['INSTALLED_MODULES_DIR']) / 'agents-system.json'
            if record != expected_record or record.is_symlink():
                raise InstallationError(f"Obcy rejestr modułów: {record}")
            if record.exists():
                fingerprint = previous.state['configuration'].get('installed_modules_sha256')
                if fingerprint is not None and hashlib.sha256(record.read_bytes()).hexdigest() != fingerprint:
                    raise InstallationError(f"Zmieniony rejestr modułów: {record}")
                source = configuration.package_dir / 'resources/agents-system.json'
                if fingerprint is None and source.is_file() and json.loads(record.read_text(encoding='utf-8')) != json.loads(source.read_text(encoding='utf-8')):
                    raise InstallationError(f"Zmieniony rejestr modułów: {record}")
        installer_module = Path(next(item['value'] for item in document['variables'] if item['name'] == 'MODULES_DIR')) / INSTALLER_MODULE_NAME
        validate_owned_directory(installer_module, configuration)
        raw = lifecycle_journal_configuration(configuration, previous, 'uninstall')
        raw['unit_path'] = str(unit)

        def apply(journal: InstallJournal) -> dict[str, Any]:
            if configuration.mode == 'system':
                journal.record('service_state', unit=unit.name, **self.installer._service_state(unit.name))
                self.installer._run(['systemctl', 'disable', '--now', unit.name])
            for command in commands:
                delete_path(command, journal)
            if configuration.mode == 'system':
                delete_path(unit, journal)
                self.installer._run(['systemctl', 'daemon-reload'])
                journal.record('daemon_reload')
            if record is not None:
                delete_path(record, journal)
            if configuration.mode == 'dev' and not configuration.clone_repo:
                delete_path(env.resolve(strict=False), journal)
                delete_path(installer_module, journal)
            delete_path(configuration.runtime_dir, journal)
            delete_path(configuration.config_dir, journal)
            delete_path(configuration.install_dir, journal)
            if arguments.purge_data:
                delete_path(configuration.data_dir, journal)
            return {
                'status': 'uninstalled', 'mode': configuration.mode,
                'install_dir': str(configuration.install_dir),
                'data_preserved': not arguments.purge_data, 'accounts_preserved': True,
                'commands': [],
            }

        return transaction(configuration, raw, apply, runner=self.installer.runner, effective_uid=self.installer.effective_uid)
