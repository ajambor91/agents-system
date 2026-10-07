"""Build isolated, context-dependent dependencies for one manager operation."""
from __future__ import annotations

import logging


from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from lib.configuration import Configuration
from ..context import ApplicationContext
from .agent_catalog import AgentCatalog
from .agent_config import AgentConfigService
from .agent_executor import AgentExecutor
from .agent_registry import AgentRegistryService
from .linux_user import LinuxUserService
from .process import ProcessRunner
from .runtime_config import RuntimeConfigService
from .shared_tools import SharedToolsService
from .shell import ShellService
from .state import AgentStateService
from .sudo_policy import SudoPolicyService
from .symlink import ShellLinkService
from .wakeup import WakeupService

if TYPE_CHECKING:
    from ...open_claw import AgentToolAbstract


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentServices:
    runner: ProcessRunner
    state: AgentStateService
    catalog: AgentCatalog
    configuration: AgentConfigService
    executor: AgentExecutor
    registry: AgentRegistryService
    runtime: RuntimeConfigService
    linux_users: LinuxUserService
    shared_tools: SharedToolsService
    shell: ShellService
    links: ShellLinkService
    sudo_policy: SudoPolicyService
    wakeup: WakeupService
    agent_tool: AgentToolAbstract
    messages: list[str]


class AgentServicesFactory:
    def __init__(self, configuration: Configuration, agent_tool: AgentToolAbstract, *,
                 runner_factory: Callable[..., ProcessRunner] = ProcessRunner) -> None:
        self._configuration = configuration
        self._repo_root = Path(type(configuration).APP_DIR).expanduser().resolve()
        self._agent_tool = agent_tool
        self._runner_factory = runner_factory

    def create_context(self, flags: Mapping[str, Any]) -> ApplicationContext:
        return ApplicationContext.create(
            self._repo_root, configuration=self._configuration,
            gateway_user=flags.get('gateway_user'),
        )

    def create(self, context: ApplicationContext, flags: Mapping[str, Any]) -> AgentServices:
        messages: list[str] = []
        runner = self._runner_factory(verbose=flags.get('verbose', False), reporter=messages.append)
        state = AgentStateService(context, runner)
        LOGGER.debug("Creating agent services: agents_root=%s", context.agents_root)
        catalog_root = Path(flags['path']).parent if flags.get('path') is not None else context.agents_root
        catalog = AgentCatalog(catalog_root)
        tool = self._agent_tool.for_user(context.gateway_user, runner)
        return AgentServices(
            runner=runner, state=state, catalog=catalog,
            configuration=AgentConfigService(catalog), executor=AgentExecutor(runner),
            registry=AgentRegistryService(context, state, tool), runtime=RuntimeConfigService(state),
            linux_users=LinuxUserService(runner), shared_tools=SharedToolsService(runner),
            shell=ShellService(state), links=ShellLinkService(runner),
            sudo_policy=SudoPolicyService(runner), wakeup=WakeupService(context, runner, self._agent_tool),
            agent_tool=tool, messages=messages,
        )
