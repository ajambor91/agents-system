"""Typed values shared by installation and rollback."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Account:
    name: str
    uid: int
    gid: int
    home: Path
    shell: str


@dataclass(frozen=True)
class InstallConfiguration:
    mode: str
    package_dir: Path
    app_name: str
    invoker: Account
    user_system: str
    user_group: str
    user_home: Path
    install_dir: Path
    config_dir: Path
    data_dir: Path
    runtime_dir: Path
    commands_dir: Path
    bash_source: str
    force: bool
    dedicated_user: bool
    clone_repo: bool
    verbose: bool

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["package_dir"] = str(self.package_dir)
        value["user_home"] = str(self.user_home)
        value["install_dir"] = str(self.install_dir)
        value["config_dir"] = str(self.config_dir)
        value["data_dir"] = str(self.data_dir)
        value["runtime_dir"] = str(self.runtime_dir)
        value["commands_dir"] = str(self.commands_dir)
        value["invoker"]["home"] = str(self.invoker.home)
        return value
