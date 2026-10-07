from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app.services.process import ProcessRunner
from .abstract import AgentToolAbstract
from .backend import OpenClawBackend


class OpenClawFacade(AgentToolAbstract):
    """Single public adapter for OpenClaw commands."""

    def __init__(self, gateway_user: str | None = None, process_runner: ProcessRunner | None = None) -> None:
        self._backend = OpenClawBackend(gateway_user=gateway_user, process_runner=process_runner) if gateway_user is not None else None

    def for_user(self, gateway_user: str, process_runner: ProcessRunner) -> AgentToolAbstract:
        return OpenClawFacade(gateway_user, process_runner)

    def _get_backend(self) -> OpenClawBackend:
        if self._backend is None:
            raise RuntimeError("Agent tool must be bound to a gateway user.")
        return self._backend

    def add_agent(self, *, name: str, workspace: Path, model: str | None=None, force: bool=False, dry_run: bool=False) -> None:
        return self._get_backend().add_agent(name=name, workspace=workspace, model=model, force=force, dry_run=dry_run)

    def list_agents(self) -> list[dict]:
        return self._get_backend().list_agents()

    def apply_identity(self, *, name: str, workspace: Path, dry_run: bool=False) -> None:
        return self._get_backend().apply_identity(name=name, workspace=workspace, dry_run=dry_run)

    def install_executor_plugin(self, plugin_root: Path, *, snapshot_root: Path, dry_run: bool=False) -> None:
        return self._get_backend().install_executor_plugin(plugin_root, snapshot_root=snapshot_root, dry_run=dry_run)

    def set_agent_tools(self, name: str, policy: dict, *, dry_run: bool=False) -> None:
        return self._get_backend().set_agent_tools(name, policy, dry_run=dry_run)

    def get_agent_tools(self, name: str) -> dict:
        return self._get_backend().get_agent_tools(name)

    def run_agent(self, *, agent_name: str, session_key: str, message_file: Path, timeout: int) -> CompletedProcess[str]:
        return self._get_backend().run_agent(agent_name=agent_name, session_key=session_key, message_file=message_file, timeout=timeout)
