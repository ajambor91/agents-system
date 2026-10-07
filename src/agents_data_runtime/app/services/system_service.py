import shutil

from lib.configuration import Configuration
import os
import sys
import subprocess
import grp
import pwd
from pathlib import Path
class SystemService:
    _TEMP_DIR: str = "/tmp/agents-system"
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
        subprocess.run(cmd, check=True, capture_output=True, text=True)
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

        subprocess.run(
            ["userdel", "--remove", "--", agent_name],
            check=True,
            capture_output=True,
            text=True,
        )
        return True

    def create_source_path(self, agent_source) -> Path:
        agent_source = Path(agent_source)
        return agent_source

    def create_temp_dir(self,agent_name: str) -> Path: 
        temp_path = Path(f"{self._TEMP_DIR}/{agent_name}")
        self.remove_data(temp_path)
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path


    def create_target_path(self,agent_name: str) -> Path:
        agent_target = Path(f"{type(self._configuration).APP_DATA_DIR}/{agent_name}")
        if agent_target.is_dir():
            raise Exception("Agent exists")
        agent_target.mkdir(parents=True, exist_ok=True)
        return agent_target

    def copy_temp_files(self,temp_path: Path, agent_source: Path) -> bool:
        shutil.copytree(agent_source, temp_path, dirs_exist_ok=True)
        return True
        

    def copy_agents_files(self, temp_path: Path, target_path: Path) -> bool:
 
        shutil.copytree(temp_path, target_path, dirs_exist_ok=True)
        return True


    def remove_data(self, path: Path) -> bool:
            if path.is_dir():
                shutil.rmtree(path)
            return True
