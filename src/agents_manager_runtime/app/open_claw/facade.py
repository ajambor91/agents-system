from __future__ import annotations

import logging
from pathlib import Path
from subprocess import CompletedProcess
import subprocess


LOGGER = logging.getLogger(__name__)


class OpenClawFacade:
    _IDENTITY_FILE = 'IDENTITY.md'
    """Single public adapter for OpenClaw commands."""
    _gateway_user: str
    def __init__(self) -> None:
        self._gateway_user =  'adam'
    


    def add_agent(self, name: str, workspace: Path, model: str,  force: bool=False) -> bool:
        LOGGER.debug('Starting facade.add_agent name=%s force=%s', name, force)
        command = [
            "openclaw", "agents", "add", name, "--workspace", workspace, "--model", model, "--non-interactive", "--json" 
        ]
        
        return self._run_as_user(command) and True


    def remove_agent(self, name: str):
        command = [
            "openclaw", "agents", "delete", name, "--force", "--json" 
        ]
                
        return self._run_as_user(command) and True
 
    def apply_identity(self, agent_name: str, agent_home: str, dry_run: bool=False) -> bool:
        command = ['openclaw', 'agents', 'set-identity', '--agent', agent_name, '--identity-file', f"{agent_home}/{self._IDENTITY_FILE}" ,'--from-identity', '--json']
        LOGGER.debug('Starting facade.apply_identity name=%s dry_run=%s', agent_name, dry_run)
        return self._run_as_user(command) and True

    # def install_executor_plugin(self, plugin_root: Path, *, snapshot_root: Path, dry_run: bool=False) -> None:
    #     LOGGER.debug('Starting facade.install_executor_plugin dry_run=%s', dry_run)
    #     return self._get_backend().install_executor_plugin(plugin_root, snapshot_root=snapshot_root, dry_run=dry_run)

    # def set_agent_tools(self, name: str, policy: dict, *, dry_run: bool=False) -> None:
    #     LOGGER.debug('Starting facade.set_agent_tools name=%s dry_run=%s', name, dry_run)
    #     return self._get_backend().set_agent_tools(name, policy, dry_run=dry_run)

    # def get_agent_tools(self, name: str) -> dict:
    #     LOGGER.debug('Starting facade.get_agent_tools name=%s', name)
    #     return self._get_backend().get_agent_tools(name)

    def run_agent(self,agent_name: str, message: str, timeout: int) -> str:
        LOGGER.debug('Starting facade.run_agent agent_name=%s timeout=%s', agent_name, timeout)
        command = ['openclaw', 'agent', '--agent', agent_name, '--message', message ]
        return self._run_as_user(command).stdout

    def _run_as_user(self, command: list[str]) -> CompletedProcess[str]:
        user_command = [
            "runuser",
            "-u", self._gateway_user,
            "--",
            "/bin/bash",
            "-ilc",
            'exec "$@"',
            "bash",
            *command,
        ]
        try:
            result = subprocess.run(
                user_command,
                check=True,
                capture_output=True,
                text=True,
                )
            if result.returncode != 0:
                message = {
                    'err' : (result.stderr or "").strip(),
                    'out': (result.stdout or "").strip(),
                    'det': f"Command failed, error code: {result.returncode}"
                }
                LOGGER.error({'msg': "Agent command success", 'details': message})

                raise Exception(message)
            LOGGER.debug({'msg': "Success", 'details': result.stdout})

            return result 
        except subprocess.CalledProcessError as e:

            message = {
                     'err' : (e.stderr or "").strip(),
                     'out': (e.stdout or "").strip(),
                     'det': f"Command failed, error code: {e.returncode}"
                 }
            LOGGER.error({'msg': "Agent command failed", 'details': message})

            raise RuntimeError(message) from e
    

