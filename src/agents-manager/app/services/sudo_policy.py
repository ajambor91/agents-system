from __future__ import annotations

import shutil
import tempfile

from pathlib import Path

from app.services.process import (
    ProcessRunner,
)


class SudoPolicyService:

    def __init__(
        self,
        runner: ProcessRunner,
    ) -> None:

        self.runner = runner

    def install(
        self,
        *,
        agent_name: str,
        gateway_user: str,
        agent_user: str,
        shell: Path,
        dry_run: bool = False,
    ) -> None:

        if (
            gateway_user
            == agent_user
        ):
            return

        destination = (
            Path("/etc/sudoers.d")
            / f"agent-manager-{agent_name}"
        )

        content = (
            f"{gateway_user} "
            f"ALL=({agent_user}) "
            f"NOPASSWD: {shell}\n"
        )

        if dry_run:
            print(
                "[DRY] install sudoers "
                f"policy {destination}: "
                f"{content.strip()}"
            )
            return

        if shutil.which(
            "visudo"
        ) is None:

            raise RuntimeError(
                "visudo not found."
            )

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
                "visudo",
                "-cf",
                str(temporary_path),
            ])

            self.runner.run_privileged([
                "install",
                "-o",
                "root",
                "-g",
                "root",
                "-m",
                "0440",

                str(temporary_path),
                str(destination),
            ])

        finally:

            temporary_path.unlink(
                missing_ok=True
            )
