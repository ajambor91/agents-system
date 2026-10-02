from __future__ import annotations

import os
import pwd
import shutil

from dataclasses import dataclass
from pathlib import Path

from lib.configuration import Configuration


@dataclass(frozen=True)
class ApplicationContext:
    repo_root: Path
    agents_root: Path

    state_root: Path
    state_owner: str
    state_owner_home: Path

    gateway_user: str
    gateway_home: Path

    openclaw_bin: Path

    @classmethod
    def create(
        cls,
        repo_root: Path,
        *,
        configuration: Configuration,
        gateway_user: str | None = None,
    ) -> "ApplicationContext":

        repo_root = repo_root.expanduser().resolve()

        gateway_user = (
            gateway_user
            or cls._detect_gateway_user()
        )
        gateway_entry = pwd.getpwnam(
            gateway_user
        )

        settings = type(configuration)
        state_owner = settings.USER_SYSTEM

        try:
            state_entry = pwd.getpwnam(
                state_owner
            )
        except KeyError as exc:
            raise RuntimeError(
                f"State owner Linux user does not exist: "
                f"{state_owner}"
            ) from exc

        state_root = Path(settings.APP_DATA_DIR).expanduser()

        gateway_home = Path(
            gateway_entry.pw_dir
        )

        return cls(
            repo_root=repo_root,
            agents_root=repo_root / "agents",

            state_root=state_root,
            state_owner=state_owner,
            state_owner_home=Path(
                state_entry.pw_dir
            ),

            gateway_user=gateway_user,
            gateway_home=gateway_home,

            openclaw_bin=cls._find_openclaw(
                gateway_home
            ),
        )

    @staticmethod
    def _detect_gateway_user() -> str:

        sudo_user = os.environ.get(
            "SUDO_USER"
        )

        if (
            os.geteuid() == 0
            and sudo_user
            and sudo_user != "root"
        ):
            return sudo_user

        return pwd.getpwuid(
            os.geteuid()
        ).pw_name

    @staticmethod
    def _find_openclaw(
        gateway_home: Path,
    ) -> Path:

        candidates: list[Path] = []

        candidates.append(
            gateway_home
            / ".openclaw"
            / "bin"
            / "openclaw"
        )

        path_binary = shutil.which(
            "openclaw"
        )

        if path_binary:
            candidates.append(
                Path(path_binary)
            )

        for candidate in candidates:

            if (
                candidate.is_file()
                and os.access(
                    candidate,
                    os.X_OK,
                )
            ):
                return candidate.resolve()

        raise RuntimeError(
            "OpenClaw CLI not found."
        )