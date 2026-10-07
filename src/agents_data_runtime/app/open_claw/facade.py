from __future__ import annotations

import logging
from lib.configuration import Configuration
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, TYPE_CHECKING
import subprocess



LOGGER = logging.getLogger(__name__)


class OpenClawFacade:
    """Single public adapter for OpenClaw commands."""
    _gateway_user: str
    def __init__(self) -> None:
        self._gateway_user =  'adam'
    


    def add_agent(self, name: str, workspace: Path, model: str,  force: bool=False) -> None:
        LOGGER.debug('Starting facade.add_agent name=%s force=%s', name, force)
        command = [
            "openclaw", "agents", "add", name, "--workspace", workspace, "--model", model, "--non-interactive", "--json" 
        ]
        
        return self._run_as_user(command)

    def remove_agent(self, name):
        command = [
            "openclaw", "agents", "delete", name, "--force", "--json" 
        ]
                
        return self._run_as_user(command)
    # def list_agents(self) -> list[dict]:
    #     LOGGER.debug('Starting facade.list_agents')
    #     return self._get_backend().list_agents()

    # def apply_identity(self, *, name: str, workspace: Path, dry_run: bool=False) -> None:
    #     LOGGER.debug('Starting facade.apply_identity name=%s dry_run=%s', name, dry_run)
    #     return self._get_backend().apply_identity(name=name, workspace=workspace, dry_run=dry_run)

    # def install_executor_plugin(self, plugin_root: Path, *, snapshot_root: Path, dry_run: bool=False) -> None:
    #     LOGGER.debug('Starting facade.install_executor_plugin dry_run=%s', dry_run)
    #     return self._get_backend().install_executor_plugin(plugin_root, snapshot_root=snapshot_root, dry_run=dry_run)

    # def set_agent_tools(self, name: str, policy: dict, *, dry_run: bool=False) -> None:
    #     LOGGER.debug('Starting facade.set_agent_tools name=%s dry_run=%s', name, dry_run)
    #     return self._get_backend().set_agent_tools(name, policy, dry_run=dry_run)

    # def get_agent_tools(self, name: str) -> dict:
    #     LOGGER.debug('Starting facade.get_agent_tools name=%s', name)
    #     return self._get_backend().get_agent_tools(name)

    # def run_agent(self, *, agent_name: str, session_key: str, message_file: Path, timeout: int) -> CompletedProcess[str]:
    #     LOGGER.debug('Starting facade.run_agent agent_name=%s timeout=%s', agent_name, timeout)
    #     return self._get_backend().run_agent(agent_name=agent_name, session_key=session_key, message_file=message_file, timeout=timeout)

    def _run_as_user(self, command: list[str]):
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
        return subprocess.run(user_command, check=True)

