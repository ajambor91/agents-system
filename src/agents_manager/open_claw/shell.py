"""Resolve and execute OpenClaw inside the gateway user's normal Bash shell."""
from __future__ import annotations

import logging

import pwd
from subprocess import CompletedProcess

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..app.services.process import ProcessRunner


LOGGER = logging.getLogger(__name__)


class OpenClawShell:
    # Fixed shell code: arguments remain separate positional parameters.
    SCRIPT = 'binary=$(type -P openclaw) || { printf "%s\n" "OpenClaw CLI not found in gateway shell." >&2; exit 127; }; exec "$binary" "$@"'

    def __init__(self, gateway_user: str, runner: ProcessRunner) -> None:
        self._gateway_user = gateway_user
        self._runner = runner

    def run(self, command: list[str], *, check: bool = True, capture: bool = False,
            timeout: int | float | None = None) -> CompletedProcess[str]:
        LOGGER.info('Starting shell.run timeout=%s', timeout)
        user = pwd.getpwnam(self._gateway_user)
        return self._runner.run_as_user(
            self._gateway_user,
            ['env', f'HOME={user.pw_dir}', f'USER={user.pw_name}', f'LOGNAME={user.pw_name}',
             '/bin/bash', '-ilc', self.SCRIPT, 'openclaw', *command[1:]],
            check=check, capture=capture, timeout=timeout,
        )
