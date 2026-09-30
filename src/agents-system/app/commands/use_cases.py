"""Public command use-cases; parsing and rendering remain outside these classes."""

from __future__ import annotations

import json
import re
from typing import Any

from ..errors import InputError
from ..models import CommandRequest, CommandResult
from ..services.environment import EnvironmentService
from ..services.installation import InstallationService
from ..services.status import StatusService
from ..services.system import ModuleRuntimeService
from ..services.users import UserService


class UseCase:
    def __init__(
        self,
        environment: EnvironmentService,
        runtime: ModuleRuntimeService,
        status: StatusService,
        users: UserService,
        installation: InstallationService,
    ) -> None:
        self.environment = environment
        self.runtime = runtime
        self.status = status
        self.users = users
        self.installation = installation


class AppAdd(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.add_module(request.arguments)


class AppCall(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.call_module(request.arguments)


class AppList(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.list_modules()


class AppRemove(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.remove_module(request.arguments)


class ConsoleDispatch(UseCase):
    """Validate an app_api envelope at the control-plane boundary."""

    NAME = re.compile(r"^[a-z][a-z0-9-]*$")

    def execute(self, request: CommandRequest) -> CommandResult:
        envelope = request.arguments.get("request")
        if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
            raise InputError("console-dispatch wymaga obiektu request ze schema_version=1")
        for field in ("section", "module_name", "command"):
            value = envelope.get(field)
            if not isinstance(value, str) or not self.NAME.fullmatch(value):
                raise InputError(f"Nieprawidłowe pole request.{field}")
        if not isinstance(envelope.get("arguments"), dict) or not isinstance(envelope.get("argv"), list):
            raise InputError("request.arguments musi być obiektem, a request.argv tablicą")
        response = {
            "ok": True,
            "status": "not-implemented",
            "message": "Not implemented yet.",
            "target": {
                "section": envelope["section"],
                "module_name": envelope["module_name"],
                "command": envelope["command"],
            },
            "request_id": request.request_id,
        }
        return CommandResult(
            stdout=json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n",
            data=response,
        )


class EnvInit(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        result = self.environment.initialize(
            use_default=bool(request.arguments["default"]),
            file=request.arguments.get("file"),
            interactive=bool(request.arguments["interactive"]),
            force=bool(request.arguments.get("force")),
        )
        self.runtime.refresh_paths()
        return CommandResult(stdout=json.dumps(result, ensure_ascii=False, indent=2) + "\n", data=result)


class EnvExport(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        values = self.environment.load_values(
            local=bool(request.arguments.get("local")),
            file=request.arguments.get("file"),
        )
        return CommandResult(stdout=self.environment.render_exports(values), data=values)


class GetVar(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        result = self.environment.get(
            request.arguments.get("name"),
            local=bool(request.arguments.get("local")),
        )
        if isinstance(result, dict):
            output = "".join(f"{name}={value}\n" for name, value in sorted(result.items()))
        else:
            output = result + "\n"
        return CommandResult(stdout=output, data=result)


class Install(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.installation.install(request.arguments)


class Reinstall(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.installation.install(request.arguments, reinstall=True)


class RuntimeStart(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.runtime_start()


class RuntimeStatus(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.runtime_status()


class RuntimeStop(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.runtime.runtime_stop()


class SystemStatus(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.status.report(request.arguments)


class UserCreate(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.users.create(request.arguments)


class UserGet(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.users.get(request.arguments)


class UserList(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.users.list()


class UserSet(UseCase):
    def execute(self, request: CommandRequest) -> CommandResult:
        return self.users.set(request.arguments)


COMMAND_TYPES: dict[str, type[UseCase]] = {
    command_type.__name__: command_type
    for command_type in (
        AppAdd,
        AppCall,
        AppList,
        AppRemove,
        ConsoleDispatch,
        EnvInit,
        EnvExport,
        GetVar,
        Install,
        Reinstall,
        RuntimeStart,
        RuntimeStatus,
        RuntimeStop,
        SystemStatus,
        UserCreate,
        UserGet,
        UserList,
        UserSet,
    )
}
