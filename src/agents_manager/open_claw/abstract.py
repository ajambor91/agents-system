from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app.services.process import ProcessRunner
from abc import ABC, abstractmethod


class AgentToolAbstract(ABC):
    """Replaceable agent tool API used by manager services."""

    @abstractmethod
    def for_user(self, gateway_user: str, process_runner: ProcessRunner) -> AgentToolAbstract:
        raise NotImplementedError

    @abstractmethod
    def add_agent(self, *, name: str, workspace: Path, model: str | None=None, force: bool=False, dry_run: bool=False) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_agents(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def apply_identity(self, *, name: str, workspace: Path, dry_run: bool=False) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_executor_plugin(self, plugin_root: Path, *, snapshot_root: Path, dry_run: bool=False) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_agent_tools(self, name: str, policy: dict, *, dry_run: bool=False) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_agent_tools(self, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def run_agent(self, *, agent_name: str, session_key: str, message_file: Path, timeout: int) -> CompletedProcess[str]:
        raise NotImplementedError
