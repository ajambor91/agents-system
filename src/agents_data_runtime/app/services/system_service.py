import shutil
import os
import sys
import subprocess
import grp
import pwd

from pathlib import Path
from lib.configuration import Configuration


class SystemService:
    _TEMP_DIR: str = "/dev/shm/agents-system"
    _configuration: Configuration

    def __init__(self, configuration: Configuration):
        self._configuration = configuration

    def create_agent_user(
        self,
        agent_name: str,
        agent_group: str,
        agent_home: str,
        execution_shell: str
    ):
        try:
            pwd.getpwnam(agent_name)
        except KeyError:
            pass
        else:
            raise FileExistsError(f"User {agent_name!r} already exists")

        try:
            grp.getgrnam(agent_group)
        except KeyError:
            subprocess.run(
                ["groupadd", agent_group],
                check=True,
                capture_output=True,
                text=True,
            )

        cmd = [
            "useradd",
            "-m",
            "-d", agent_home,
            "-s", execution_shell,
            "-g", agent_group,
            agent_name,
        ]
        return self._run_command(cmd)
    
    def set_dir_privs(self, agent_home: Path,agent_name: str, user_name: str = 'adam') -> bool:
        if not agent_home.is_absolute() or ".." in agent_home.parts:
            raise ValueError("Agent home must be an absolute path without '..'")
        agent_home = agent_home.resolve(strict=True)
        if agent_home == Path("/") or not agent_home.is_dir():
            raise ValueError("Agent home must be an existing directory other than '/'")
        pwd.getpwnam(user_name)
        home_path = str(agent_home)
        self._run_command(['chmod', '0750', '--', home_path])
        self._run_command(['setfacl', '-m', f'u:{user_name}:rwx', '--', home_path])
        self._run_command([
            'setfacl', '-d', '-m',
            f'u:{user_name}:rwx,u:{agent_name}:rwx', '--', home_path,
        ])
        return True

    def remove_agent_user(self, agent_name: str) -> bool:
        """Remove an agent account, its home directory and mail spool."""
        if not isinstance(agent_name, str) or not agent_name or agent_name.startswith("-"):
            raise ValueError("Agent username must be a non-empty name, not an option")
        try:
            account = pwd.getpwnam(agent_name)
        except KeyError as exc:
            raise FileNotFoundError(f"User {agent_name!r} does not exist") from exc
        if account.pw_uid == 0:
            raise ValueError("Cannot remove a root account")
        home = Path(account.pw_dir)
        if not home.is_absolute() or ".." in home.parts or home == Path("/"):
            raise ValueError(f"Invalid home directory for user {agent_name!r}: {home}")
        command = ["userdel", "--remove", "--", agent_name]
        return self._run_command(command)

    def _run_command(self, command: list[str]) -> bool:
        try:
            subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            return True
        except subprocess.CalledProcessError as e:
            message = (
                (e.stderr or "").strip()
                    or (e.stdout or "").strip()
                    or f"Command failed, error code: {e.returncode}"
                )
            raise RuntimeError(message) from e

    def create_source_path(self, agent_source) -> Path:
        agent_source = Path(agent_source)
        return agent_source

    def create_temp_dir(self, agent_name: str) -> Path:
        temp_path = Path(f"{self._TEMP_DIR}/{agent_name}")
        self.remove_data(temp_path)
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path

    def create_target_path(self, agent_name: str) -> Path:
        agent_target = Path(f"{type(self._configuration).APP_DATA_DIR}/{agent_name}")
        if agent_target.is_dir():
            raise Exception("Agent exists")
        agent_target.mkdir(parents=True, exist_ok=True)
        return agent_target

    def get_temp_path(self, agent_name: str) -> Path | None:
        try:
            agent_target = Path(f"{type(self._configuration).APP_DATA_DIR}/{agent_name}")
            if agent_target.is_dir():
                return agent_target
            raise  Exception("Temp path does not exist")
        except Exception:
            return None
        
    def get_source_path(self, path: str) -> Path:
        agent_source = Path(path)
        if agent_source.is_dir():
            return agent_source
        raise  Exception("Source path does not exist")

    def _write_temp_file(
        self,
        temp_path: Path,
        filename: str,
        content: str | bytes
    ) -> Path:
        target = temp_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")

        return target

    def copy_temp_files(
        self,
        temp_path: Path,
        agent_source: Path
    ) -> bool:
        shutil.copytree(agent_source, temp_path, dirs_exist_ok=True)
        return True

    def copy_agents_files(
        self,
        temp_path: Path,
        target_path: Path
    ) -> bool:
        shutil.copytree(temp_path, target_path, dirs_exist_ok=True)
        return True

    def remove_data(self, path: Path) -> bool:
        print("REMOVE TEMP")
        print(path)
        if path.is_dir():
            shutil.rmtree(path)
        return True