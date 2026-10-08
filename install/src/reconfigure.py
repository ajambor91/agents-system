"""Validate and apply an environment document without moving installation roots."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
from typing import Any
import grp
import pwd

from .parent import InstallerParent
from .enums import InstallerMode
from .installer import Installer
from .journal import InstallJournal
from .consts import ENVIRONMENT_FILE
from .shared.lifecycle import (
    validate_dev_runtime_stopped,
    configuration_from_journal, environment_values, lifecycle_journal_configuration,
    read_environment, require_root, transaction, validate_environment_identity,
    validate_owned_installation, validate_managed_unit,
)


class Reconfigure(InstallerParent):
    operation = InstallerMode.RECONFIGURE

    def __init__(self, *, installer: Installer | None = None, **installer_options: Any) -> None:
        self.installer = installer or Installer(**installer_options)

    def execute(self, arguments: argparse.Namespace) -> dict[str, Any]:
        self.require_yes(arguments)
        # Validate --envs immediately, before reading a journal or touching services.
        document = read_environment(arguments.envs)
        require_root(self.installer.effective_uid)
        previous = InstallJournal.open(Path(arguments.journal))
        configuration = configuration_from_journal(previous, verbose=arguments.verbose)
        validate_owned_installation(configuration)
        current = read_environment(configuration.config_dir / ENVIRONMENT_FILE)
        validate_environment_identity(document, configuration, previous=current)
        validate_dev_runtime_stopped(current, configuration)
        configuration = replace(configuration, bash_source=environment_values(document)['BASH_SOURCE'])
        self.installer.package_dir = configuration.package_dir
        self.installer.verbose = configuration.verbose
        self.installer._validate_sources(configuration.mode)
        unit_path = self.installer.unit_root / f'{configuration.app_name}.service'
        if configuration.mode == 'system':
            validate_managed_unit(unit_path, configuration)
        raw = lifecycle_journal_configuration(configuration, previous, 'reconfigure')
        raw['unit_path'] = str(unit_path)
        account = pwd.getpwnam(configuration.user_system)
        group = grp.getgrnam(configuration.user_group)

        def apply(journal: InstallJournal) -> dict[str, Any]:
            self.installer._quiesce_service(configuration, journal)
            self.installer._render_resources(configuration, journal, environment_document=document)
            self.installer._generate_configuration(configuration, journal)
            self.installer._set_ownership(configuration.config_dir, account.pw_uid, group.gr_gid, configuration.mode)
            if configuration.mode == 'system':
                self.installer._install_unit(configuration, journal)
            self.installer._write_absolute_config_pointer(configuration, journal, owner_id=account.pw_uid, group_id=group.gr_gid)
            if configuration.mode == 'system':
                self.installer._activate_service(configuration, journal)
            outputs = self.installer._verify(configuration)
            outputs['status'] = 'reconfigured'
            return outputs

        return transaction(configuration, raw, apply, runner=self.installer.runner, effective_uid=self.installer.effective_uid)
