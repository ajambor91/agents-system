"""System status report service."""

from __future__ import annotations

import contextlib
import io
from typing import Any

from ..errors import AgentsSystemError
from ..models import CommandResult
from runtime import service as runtime


class StatusService:
    """Build and render the read-only aggregate system report."""

    def report(self, values: dict[str, Any]) -> CommandResult:
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = runtime.print_system_status(runtime.system_status(), bool(values.get("json")))
        except runtime.RuntimeErrorMessage as exc:
            raise AgentsSystemError(str(exc)) from exc
        return CommandResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())
