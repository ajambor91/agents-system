"""Adapters for the established runtime, status and operating-system services."""

from __future__ import annotations

import contextlib
import io
import json
from types import SimpleNamespace
from typing import Any, Callable

from ..errors import AgentsSystemError
from ..models import CommandResult
from runtime import service as runtime
from shared.configuration import ApplicationEnvironment


class ModuleRuntimeService:
    """Expose module-registry and runtime operations without printing from Application."""

    def __init__(self, configuration: ApplicationEnvironment | None = None) -> None:
        self.configuration = configuration
        self.refresh_paths(configuration)

    @staticmethod
    def refresh_paths(configuration: ApplicationEnvironment | None = None) -> None:
        if configuration is None:
            return
        runtime.configure(configuration)

    def invoke(self, function: Callable[..., int], *args: Any) -> CommandResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = function(*args)
        except runtime.RuntimeErrorMessage as exc:
            raise AgentsSystemError(str(exc)) from exc
        return CommandResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def add_module(self, values: dict[str, Any]) -> CommandResult:
        return self.invoke(
            runtime.add_module,
            SimpleNamespace(
                name=values["name"],
                repository_path=values.get("repository_path"),
                entrypoint=values.get("entrypoint"),
                start=values.get("start", False),
            ),
        )

    def list_modules(self) -> CommandResult:
        return CommandResult(stdout=json.dumps(runtime.read_registry(), ensure_ascii=False) + "\n")

    def remove_module(self, values: dict[str, Any]) -> CommandResult:
        return self.invoke(runtime.remove_module, SimpleNamespace(name=values["name"]))

    def call_module(self, values: dict[str, Any]) -> CommandResult:
        payload = values.get("payload", {})
        return self.invoke(
            runtime.call_module,
            SimpleNamespace(name=values["name"], payload=json.dumps(payload, ensure_ascii=False)),
        )

    def runtime_start(self) -> CommandResult:
        return self.invoke(runtime.start_runtime)

    def runtime_stop(self) -> CommandResult:
        return self.invoke(runtime.stop_runtime)

    def runtime_status(self) -> CommandResult:
        return CommandResult(stdout=json.dumps(runtime.runtime_status(), ensure_ascii=False) + "\n")
