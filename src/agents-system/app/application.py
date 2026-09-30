"""The sole Agents System composition root."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from .command import Command
from .commands import COMMAND_TYPES
from .errors import InputError
from .models import CommandRequest, CommandResult
from .services.environment import EnvironmentService
from .services.installation import InstallationService
from .services.status import StatusService
from .services.system import ModuleRuntimeService
from .services.users import UserService
from shared.configuration import ApplicationEnvironment, ConfigurationValueError


class Application:
    """Validate definitions, construct services and dispatch typed requests."""

    def __init__(
        self,
        *,
        repository_root: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.repository_root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
        self.environment_mapping = os.environ if environment is None else environment
        self.environment_service = EnvironmentService(self.repository_root)
        try:
            self.configuration = ApplicationEnvironment.discover(
                self.repository_root, environment=self.environment_mapping
            )
        except ConfigurationValueError:
            self.configuration = None
        self.runtime_service = ModuleRuntimeService(self.configuration)
        self.status_service = StatusService()
        self.user_service = UserService()
        self.installation_service = InstallationService(self.repository_root)
        self.command_types = COMMAND_TYPES
        self.specs = Command.load_specs(
            self.repository_root / "src" / "agents-system" / "app" / "specs",
            set(COMMAND_TYPES),
        )
        self._commands = {
            name: command_type(
                self.environment_service,
                self.runtime_service,
                self.status_service,
                self.user_service,
                self.installation_service,
            )
            for name, command_type in COMMAND_TYPES.items()
        }

    def execute(self, request: CommandRequest) -> CommandResult:
        spec = self.specs[request.command]
        target = spec["target"]["command_class"]
        return self._commands[target].execute(request)

    def run(self, arguments: Sequence[str]) -> CommandResult:
        argv = list(arguments)
        if not argv:
            names = "\n".join(f"  {name:<18} {spec.get('description', '')}" for name, spec in self.specs.items())
            return CommandResult(exit_code=2, stderr="Użycie: agents-system <komenda> [flagi]\n\nKomendy:\n" + names + "\n")
        name = argv.pop(0).replace("_", "-")
        name = {
            "add": "app-add",
            "call": "app-call",
            "list": "app-list",
            "remove": "app-remove",
            "start": "runtime-start",
            "status": "runtime-status",
            "stop": "runtime-stop",
        }.get(name, name)
        if name not in self.specs:
            raise InputError(f"Nieznana komenda: {name}")
        parser = Command(
            self.specs[name],
            environment=self.environment_mapping,
            variable_resolver=self._get_var,
            environment_first=bool(
                self.configuration and self.configuration.shell_source_enabled
            ),
        )
        request = parser.parse(argv)
        if request is None:
            return CommandResult(stdout=parser.help())
        return self.execute(request)

    def _get_var(self, name: str) -> str | None:
        try:
            value = self.environment_service.get(name)
        except Exception:
            return None
        return value if isinstance(value, str) else None
