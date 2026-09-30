"""Operating-system user management service."""

from __future__ import annotations

import contextlib
import io
from types import SimpleNamespace
from typing import Any, Callable

from ..errors import AgentsSystemError
from ..models import CommandResult
from runtime import service as runtime


class UserService:
    """Create and inspect system identities used by Agents System."""

    @staticmethod
    def _invoke(function: Callable[..., int], *args: Any) -> CommandResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = function(*args)
        except runtime.RuntimeErrorMessage as exc:
            raise AgentsSystemError(str(exc)) from exc
        return CommandResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def create(self, values: dict[str, Any]) -> CommandResult:
        return self._invoke(
            runtime.create_user,
            SimpleNamespace(user=values.get("user", "user-system"), yes=values.get("yes", False)),
        )

    def get(self, values: dict[str, Any]) -> CommandResult:
        return self._invoke(runtime.get_user, SimpleNamespace(**values))

    def list(self) -> CommandResult:
        return self._invoke(runtime.list_users)

    def set(self, values: dict[str, Any]) -> CommandResult:
        return self._invoke(
            runtime.set_user,
            SimpleNamespace(user=values["user"], yes=values.get("yes", False)),
        )
