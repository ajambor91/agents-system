
import subprocess
import grp
import pwd

from pathlib import Path
from lib.configuration import Configuration


class SystemService:
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



    def link_agent_files(
            self,
            source_path: Path | str,
            target_path: Path | str,
            file_extension: str | None = None
        ) -> bool:
            if isinstance(source_path, str):
                source_path = Path(source_path)
            if isinstance(target_path, str):
                target_path = Path(target_path)
            absolute_source_path = source_path.absolute()
            absolute_target_path = target_path.absolute()
            print("DEBUG_DEBUG_DEBUG_DEBUG_DEBUG_DEBUG_DEBUG_DEBUG_")
            print(absolute_source_path)
            print(absolute_target_path)
            if not absolute_source_path.exists():
                raise Exception("Source data does not exist")
    
            if not absolute_target_path.exists():
                absolute_target_path.mkdir(parents=True)
    
            if (
                absolute_source_path.is_file()
                and (
                    not file_extension
                    or absolute_source_path.suffix == file_extension
                )
            ):
                target_file = absolute_target_path / absolute_source_path.name
                if target_path.exists() and target_file.is_file():
                    target_file.unlink(missing_ok=True)
                target_file.symlink_to(absolute_source_path)
                return True
    
            if not absolute_source_path.is_dir():
                raise Exception("Cannot find any matches")
    
            pattern = f"*{file_extension}" if file_extension else "*"
    
            for file in absolute_source_path.glob(pattern):
                if not file.is_file():
                    continue
    
                target_file = absolute_target_path / file.name
                if target_path.exists() and target_file.is_file():
                    target_file.unlink(missing_ok=True)
                target_file.symlink_to(file)
    
            return True