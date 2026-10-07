from __future__ import annotations

import logging

import pwd
import re
import shutil

from dataclasses import dataclass
from pathlib import Path

from .process import (
    ProcessRunner,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinuxUser:
    name: str
    home: Path
    created: bool


class LinuxUserService:

    USER_PATTERN = re.compile(
        r"^[a-z_][a-z0-9_-]{0,31}$"
    )

    def __init__(
        self,
        runner: ProcessRunner,
    ) -> None:

        self.runner = runner

    def resolve_or_create(
        self,
        username: str,
        *,
        dry_run: bool = False,
    ) -> LinuxUser:

        LOGGER.debug('Resolving or creating runtime user username=%s dry_run=%s', username, dry_run)
        if not self.USER_PATTERN.fullmatch(
            username
        ):
            raise ValueError(
                f"Invalid Linux username: "
                f"{username}"
            )

        try:

            entry = pwd.getpwnam(
                username
            )

            return LinuxUser(
                name=username,
                home=Path(entry.pw_dir),
                created=False,
            )

        except KeyError:
            pass

        home = (
            Path("/home")
            / username
        )

        if dry_run:
            return LinuxUser(
                name=username,
                home=home,
                created=True,
            )

        self.runner.report(
            f"[+] Creating Linux user: "
            f"{username}"
        )

        self.runner.run_privileged([
            "adduser",
            "--disabled-password",
            "--gecos",
            "",
            username,
        ])

        entry = pwd.getpwnam(
            username
        )

        return LinuxUser(
            name=username,
            home=Path(entry.pw_dir),
            created=True,
        )

    def prepare_home(
        self,
        user: LinuxUser,
        *,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Preparing runtime user home dry_run=%s', dry_run)
        directories = [
            user.home / "bin",
            user.home / "scripts",
            user.home / "tools",
            user.home / "tmp",

            user.home / ".config",
            user.home / ".cache",

            user.home
            / ".local"
            / "bin",

            user.home
            / ".local"
            / "share",
        ]

        for directory in directories:

            if dry_run:
                self.runner.report(
                    f"[DRY] mkdir "
                    f"{directory}"
                )
                continue

            self.runner.run_privileged([
                "install",
                "-d",

                "-o",
                user.name,

                "-g",
                user.name,

                "-m",
                "0700",

                str(directory),
            ])

    def prepare_workspace(
        self,
        user: LinuxUser,
        workspace: Path,
        gateway_user: str,
        *,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Preparing runtime user workspace dry_run=%s', dry_run)
        if dry_run:
            self.runner.report(
                f"[DRY] create workspace "
                f"{workspace}; grant "
                f"{gateway_user} rwx"
            )
            return

        if shutil.which(
            "setfacl"
        ) is None:
            raise RuntimeError(
                "setfacl is required. "
                "Install package: acl"
            )

        self.runner.run_privileged([
            "install",
            "-d",

            "-o",
            user.name,

            "-g",
            user.name,

            "-m",
            "0700",

            str(workspace),
        ])

        # Gateway needs to traverse
        # /home/huginn.
        self.runner.run_privileged([
            "setfacl",
            "-m",
            f"u:{gateway_user}:--x",
            str(user.home),
        ])

        # Gateway can work with OpenClaw
        # bootstrap files in the workspace.
        self.runner.run_privileged([
            "setfacl",
            "-m",
            f"u:{gateway_user}:rwx",
            str(workspace),
        ])

        # New files inherit gateway access.
        self.runner.run_privileged([
            "setfacl",
            "-d",
            "-m",
            f"u:{gateway_user}:rwx",
            str(workspace),
        ])

        self.runner.run_privileged([
            "setfacl",
            "-d",
            "-m",
            f"u:{user.name}:rwx",
            str(workspace),
        ])