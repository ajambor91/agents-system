"""Privileged Agents System bootstrap installation service."""

from __future__ import annotations

import json
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..errors import AgentsSystemError
from ..models import CommandResult
from .environment import EnvironmentService


class InstallationService:
    """Prepare the system identity, checkout, environment and public wrappers."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()

    def install(self, values: dict[str, Any], *, reinstall: bool = False) -> CommandResult:
        username = str(values.get("user") or "user-system")
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", username):
            raise AgentsSystemError("Nieprawidłowa nazwa użytkownika", exit_code=2)
        if not values.get("yes"):
            return CommandResult(
                exit_code=2,
                stdout=(
                    f"Operacja przygotuje konto {username}, jego checkout, konfigurację środowiska "
                    "i linki w /usr/local/bin. Użyj --yes, aby potwierdzić.\n"
                ),
            )
        if os.geteuid() != 0:
            raise AgentsSystemError("Instalacja Agents System wymaga sudo")

        self._ensure_account(username)
        account = pwd.getpwnam(username)
        home = Path(account.pw_dir)
        for directory in (home, home / "repositories", home / ".agents"):
            directory.mkdir(parents=True, exist_ok=True)
            os.chown(directory, account.pw_uid, account.pw_gid)
            directory.chmod(0o2770)

        target = (home / "repositories" / "agents-system").resolve()
        if self.repository_root != target:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.repository_root, target, dirs_exist_ok=True, symlinks=True)
        self._chown_tree(target, account.pw_uid, account.pw_gid)
        self._publish_wrappers(target)
        environment_result = self._initialize_environment(target, username, home, reinstall=reinstall)
        result = {
            "installed": True,
            "reinstalled": reinstall,
            "user": username,
            "home": str(home),
            "repository": str(target),
            "environment": environment_result,
        }
        return CommandResult(stdout=json.dumps(result, ensure_ascii=False, indent=2) + "\n", data=result)

    @staticmethod
    def _ensure_account(username: str) -> None:
        try:
            if subprocess.run(["getent", "group", username], capture_output=True, check=False).returncode != 0:
                subprocess.run(["groupadd", "--system", username], check=True)
            if subprocess.run(["getent", "passwd", username], capture_output=True, check=False).returncode != 0:
                shell = shutil.which("nologin") or "/usr/sbin/nologin"
                subprocess.run(
                    [
                        "useradd", "--system", "--gid", username,
                        "--home-dir", f"/home/{username}", "--create-home", "--shell", shell, username,
                    ],
                    check=True,
                )
        except subprocess.CalledProcessError as exc:
            raise AgentsSystemError(
                f"Polecenie systemowe {exc.cmd[0]} zakończyło się kodem {exc.returncode}"
            ) from exc

    @staticmethod
    def _chown_tree(root: Path, uid: int, gid: int) -> None:
        for current, directories, files in os.walk(root):
            os.chown(current, uid, gid)
            for name in directories:
                path = Path(current) / name
                if not path.is_symlink():
                    os.chown(path, uid, gid)
            for name in files:
                path = Path(current) / name
                if not path.is_symlink():
                    os.chown(path, uid, gid)

    @staticmethod
    def _publish_wrappers(target: Path) -> None:
        destination_root = Path("/usr/local/bin")
        destination_root.mkdir(parents=True, exist_ok=True)
        for script in sorted((target / "host_scripts").glob("*.sh")):
            command = script.stem.replace("-", "_")
            destination = destination_root / command
            if destination.exists() and not destination.is_symlink():
                raise AgentsSystemError(f"Istnieje zwykły plik: {destination}")
            temporary = destination.with_name(destination.name + f".tmp-{os.getpid()}")
            temporary.unlink(missing_ok=True)
            temporary.symlink_to(script)
            temporary.replace(destination)

    @staticmethod
    def _initialize_environment(
        target: Path,
        username: str,
        home: Path,
        *,
        reinstall: bool,
    ) -> dict[str, Any]:
        service = EnvironmentService(target)
        if reinstall and service.local_path.is_file():
            document = service.read_document(service.local_path)
            source = str(service.local_path)
        else:
            document = service.read_document(service.template_path)
            source = str(service.template_path)
            for item in document["variables"]:
                if item["name"] == "USER_SYSTEM":
                    item["value"] = username
                elif item["name"] == "USER_SYSTEM_HOME":
                    item["value"] = str(home)
        return service.publish(document, source=source)
