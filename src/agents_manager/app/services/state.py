from __future__ import annotations

import logging

import json
import os
import shutil
import stat
import tempfile

from dataclasses import dataclass
from pathlib import Path

from ..context import (
    ApplicationContext,
)
from .process import (
    ProcessRunner,
)
from .agent_catalog import AgentCatalog


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentStatePaths:
    agent_dir: Path
    shells_dir: Path

    config_json: Path
    runtime_json: Path
    shell_json: Path

    bashrc: Path
    agentrc: Path


class AgentStateService:

    def __init__(
        self,
        context: ApplicationContext,
        runner: ProcessRunner,
    ) -> None:

        self.context = context
        self.runner = runner

    def paths(
        self,
        agent_name: str,
    ) -> AgentStatePaths:

        agent_dir = (
            self.context.state_root
            / agent_name
        )

        shells_dir = (
            agent_dir
            / "shells"
        )

        return AgentStatePaths(
            agent_dir=agent_dir,
            shells_dir=shells_dir,

            config_json=(
                agent_dir
                / "config.json"
            ),

            runtime_json=(
                agent_dir
                / "runtime.json"
            ),

            shell_json=(
                agent_dir
                / "shell.json"
            ),

            bashrc=(
                shells_dir
                / ".bashrc"
            ),

            agentrc=(
                shells_dir
                / ".agentrc"
            ),
        )

    def prepare(
        self,
        agent_name: str,
        *,
        dry_run: bool = False,
    ) -> AgentStatePaths:

        LOGGER.debug('Preparing agent state directories agent_name=%s dry_run=%s', agent_name, dry_run)
        if not isinstance(agent_name, str) or not AgentCatalog.AGENT_PATTERN.fullmatch(agent_name):
            raise ValueError(f"Invalid agent name: {agent_name}")

        paths = self.paths(
            agent_name
        )

        self.prepare_root(
            dry_run=dry_run
        )

        directories = (paths.agent_dir, paths.shells_dir)
        # Validate both destinations before creating or changing either one.
        for directory in directories:
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise ValueError(f"Invalid state directory path: {directory}")

        if dry_run:
            for directory in directories:
                self.runner.report(
                    f"[DRY] create state dir "
                    f"{directory}"
                )
            return paths

        # Relative directory descriptors keep creation inside the prepared root
        # even if a pathname is replaced after validation.
        root_fd = os.open(self.context.state_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            group_id = os.fstat(root_fd).st_gid
            agent_fd = self._prepare_directory(agent_name, root_fd, group_id)
            try:
                shells_fd = self._prepare_directory("shells", agent_fd, group_id)
                os.close(shells_fd)
            finally:
                os.close(agent_fd)
        finally:
            os.close(root_fd)

        return paths

    @staticmethod
    def _prepare_directory(name: str, parent_fd: int, group_id: int) -> int:
        try:
            os.mkdir(name, mode=0o777, dir_fd=parent_fd)
        except FileExistsError:
            pass
        directory_fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd,
        )
        try:
            metadata = os.fstat(directory_fd)
            # Correct shared directories may belong to another group member.
            # Leave them alone instead of requiring ownership or sudo.
            group_changed = metadata.st_gid != group_id
            if group_changed:
                os.fchown(directory_fd, -1, group_id)
            if group_changed or stat.S_IMODE(metadata.st_mode) != 0o777:
                os.fchmod(directory_fd, 0o777)
            return directory_fd
        except BaseException:
            os.close(directory_fd)
            raise

    def prepare_root(self, *, dry_run: bool = False) -> None:
        """The installer owns creation and permissions of the shared state root."""
        LOGGER.debug('Preparing agent state directories_root dry_run=%s', dry_run)
        if self.context.state_root.is_symlink() or not self.context.state_root.is_dir():
            raise FileNotFoundError(
                f"State directory is not prepared: {self.context.state_root}; run the system installer."
            )

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        mode: str = "0660",
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Writing agent state text path=%s mode=%s dry_run=%s', path, mode, dry_run)
        if dry_run:
            self.runner.report(
                f"[DRY] write {path} "
                f"owner="
                f"{self.context.state_owner} "
                f"mode={mode}"
            )
            return

        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"Invalid state file path: {path}")
        # Stage on the same filesystem so replacing the document is atomic.
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        try:
            temporary_path.chmod(int(mode, 8))
            os.chown(temporary_path, -1, path.parent.stat().st_gid)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def write_json(
        self,
        path: Path,
        data: dict,
        *,
        mode: str = "0660",
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Writing agent state JSON path=%s mode=%s dry_run=%s', path, mode, dry_run)
        self.write_text(
            path,
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            mode=mode,
            dry_run=dry_run,
        )

    def grant_runtime_reader(
        self,
        username: str,
        paths: AgentStatePaths,
        *,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Granting runtime read access username=%s dry_run=%s', username, dry_run)
        self._grant_file_reader(
            username,
            paths.runtime_json,
            dry_run=dry_run,
        )

    def grant_config_reader(
        self,
        username: str,
        paths: AgentStatePaths,
        *,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Granting configuration read access username=%s dry_run=%s', username, dry_run)
        self._grant_file_reader(
            username,
            paths.config_json,
            dry_run=dry_run,
        )

    def grant_shell_reader(
        self,
        username: str,
        paths: AgentStatePaths,
        *,
        dry_run: bool = False,
    ) -> None:

        LOGGER.debug('Granting shell read access username=%s dry_run=%s', username, dry_run)
        self._grant_file_reader(
            username,
            paths.agentrc,
            dry_run=dry_run,
        )

        self._grant_file_reader(
            username,
            paths.bashrc,
            dry_run=dry_run,
        )

    def _grant_file_reader(
        self,
        username: str,
        file_path: Path,
        *,
        dry_run: bool,
    ) -> None:

        state_root = self.context.state_root.absolute()
        file_path = file_path.absolute()
        try:
            relative_path = file_path.relative_to(state_root)
        except ValueError as exc:
            raise ValueError(f"State reader path is outside the state directory: {file_path}") from exc
        if (not relative_path.parts or ".." in relative_path.parts or file_path.is_symlink()
                or (file_path.exists() and not file_path.is_file())):
            raise ValueError(f"Invalid state reader file path: {file_path}")
        directories = [state_root]
        directory = state_root
        for component in relative_path.parts[:-1]:
            directory = directory / component
            directories.append(directory)
        for directory in directories:
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise ValueError(f"Invalid state reader directory path: {directory}")

        if (
            username
            == self.context.state_owner
        ):
            return

        if dry_run:
            self.runner.report(
                f"[DRY] grant {username} "
                f"read access to {file_path}"
            )
            return

        if shutil.which("setfacl") is None:
            raise RuntimeError(
                "setfacl is required. "
                "Install package: acl"
            )

        # /home/user-system can remain private.
        # We only give this user permission
        # to traverse it, not list it.
        self.runner.run_privileged([
            "setfacl",
            "-m",
            f"u:{username}:--x",
            str(
                self.context
                .state_owner_home
            ),
        ])

        # The shared root is group-private; individual agents may traverse it
        # to read explicitly granted files without joining the application group.
        for directory in directories:
            self.runner.run_privileged([
                "setfacl", "-m", f"u:{username}:--x", str(directory),
            ])

        self.runner.run_privileged([
            "setfacl",
            "-m",
            f"u:{username}:r--",
            str(file_path),
        ])
