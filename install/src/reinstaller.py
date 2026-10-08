"""Replace a managed installation transactionally, preserving its configuration."""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
from typing import Any

from .parent import InstallerParent
from .enums import InstallerMode
from .installer import Installer
from .journal import InstallJournal
from .consts import ENVIRONMENT_FILE
from .shared.lifecycle import (
    validate_dev_runtime_stopped,
    require_root, configuration_from_journal, read_environment,
    validate_owned_installation, validate_environment_identity, managed_commands,
)
from .shared import absolute


class Reinstaller(InstallerParent):
    operation = InstallerMode.REINSTALL

    def __init__(self, *, installer: Installer | None = None, **installer_options: Any) -> None:
        self.installer = installer or Installer(**installer_options)

    def execute(self, arguments: argparse.Namespace) -> dict[str, Any]:
        self.require_yes(arguments)
        require_root(self.installer.effective_uid)
        previous = InstallJournal.open(Path(arguments.journal))
        configuration = configuration_from_journal(previous, verbose=arguments.verbose)
        validate_owned_installation(configuration)
        managed_commands(previous, configuration)
        document = read_environment(configuration.config_dir / ENVIRONMENT_FILE)
        validate_environment_identity(document, configuration)
        validate_dev_runtime_stopped(document, configuration)
        if arguments.source:
            source = absolute(arguments.source, 'SOURCE', must_exist=True)
            configuration = replace(configuration, package_dir=source)
        self.installer.package_dir = configuration.package_dir
        self.installer._validate_sources(configuration.mode)
        return self.installer.install_configuration(
            configuration, environment_document=document,
            operation="reinstall", previous_journal=str(previous.root),
        )
