from __future__ import annotations

import json
import shutil
import tempfile

from dataclasses import dataclass
from pathlib import Path

from ..context import (
    ApplicationContext,
)
from .process import (
    ProcessRunner,
)


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

        paths = self.paths(
            agent_name
        )

        self.prepare_root(
            dry_run=dry_run
        )

        # 0711:
        #
        # owner can list/write,
        # other users can only traverse a known path.
        #
        # Actual files remain 0640.
        for directory in (
            paths.agent_dir,
            paths.shells_dir,
        ):

            if dry_run:
                print(
                    f"[DRY] create state dir "
                    f"{directory}"
                )
                continue

            self.runner.run_privileged([
                "install",
                "-d",
                "-o",
                self.context.state_owner,
                "-g",
                self.context.state_owner,
                "-m",
                "0711",
                str(directory),
            ])

        return paths

    def prepare_root(
        self,
        *,
        dry_run: bool = False,
    ) -> None:

        if dry_run:
            print(
                f"[DRY] create state dir "
                f"{self.context.state_root}"
            )
            return

        self.runner.run_privileged([
            "install",
            "-d",
            "-o",
            self.context.state_owner,
            "-g",
            self.context.state_owner,
            "-m",
            "0711",
            str(self.context.state_root),
        ])

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        mode: str = "0640",
        dry_run: bool = False,
    ) -> None:

        if dry_run:
            print(
                f"[DRY] write {path} "
                f"owner="
                f"{self.context.state_owner} "
                f"mode={mode}"
            )
            return

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
        ) as handle:

            handle.write(
                content
            )

            temporary_path = Path(
                handle.name
            )

        try:

            self.runner.run_privileged([
                "install",
                "-o",
                self.context.state_owner,
                "-g",
                self.context.state_owner,
                "-m",
                mode,
                str(temporary_path),
                str(path),
            ])

        finally:

            temporary_path.unlink(
                missing_ok=True
            )

    def write_json(
        self,
        path: Path,
        data: dict,
        *,
        mode: str = "0640",
        dry_run: bool = False,
    ) -> None:

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

        if (
            username
            == self.context.state_owner
        ):
            return

        if dry_run:
            print(
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

        self.runner.run_privileged([
            "setfacl",
            "-m",
            f"u:{username}:r--",
            str(file_path),
        ])
