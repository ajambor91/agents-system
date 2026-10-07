from __future__ import annotations

import logging

import os

from pathlib import Path

from .linux_user import (
    LinuxUser,
)
from .process import (
    ProcessRunner,
)
from .state import (
    AgentStatePaths,
)


LOGGER = logging.getLogger(__name__)


class ShellLinkService:

    def __init__(
        self,
        runner: ProcessRunner,
    ) -> None:

        self.runner = runner

    def link(
        self,
        user: LinuxUser,
        paths: AgentStatePaths,
        *,
        replace_existing: bool,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Linking agent shell files dry_run=%s', dry_run)
        for name, target in (
            (
                ".bashrc",
                paths.bashrc,
            ),
            (
                ".agentrc",
                paths.agentrc,
            ),
        ):
            self.link_file(
                user,
                target,
                user.home / name,
                replace_existing=replace_existing,
                dry_run=dry_run,
            )

    def link_file(
        self,
        user: LinuxUser,
        source: Path,
        destination: Path,
        *,
        replace_existing: bool,
        dry_run: bool = False,
    ) -> None:
        """Create one owned link while protecting unrelated workspace files."""
        LOGGER.debug('Linking agent shell files_file source=%s destination=%s dry_run=%s', source, destination, dry_run)
        if dry_run:
            self.runner.report(f"[DRY] ln -s {source} {destination}")
            return

        if destination.is_symlink():
            current = Path(os.readlink(destination))
            if not current.is_absolute():
                current = (destination.parent / current).resolve(strict=False)
            if current == source:
                return
            if not replace_existing:
                raise FileExistsError(
                    f"{destination} already points elsewhere; use --force."
                )
            self.runner.run_privileged(["rm", "-f", str(destination)])
        elif destination.exists():
            if not replace_existing:
                raise FileExistsError(
                    f"{destination} already exists; use --force."
                )
            if destination.is_dir():
                raise IsADirectoryError(str(destination))
            self.runner.run_privileged(["rm", "-f", str(destination)])

        self.runner.run_privileged([
            "ln",
            "-s",
            str(source),
            str(destination),
        ])
        self.runner.run_privileged([
            "chown",
            "-h",
            f"{user.name}:{user.name}",
            str(destination),
        ])
