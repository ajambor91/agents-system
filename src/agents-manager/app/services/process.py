from __future__ import annotations

import os
import pwd
import shlex
import subprocess
import sys


class ProcessRunner:

    def __init__(
        self,
        *,
        verbose: bool = False,
    ) -> None:

        self.verbose = verbose

    def run(
        self,
        command: list[str],
        *,
        check: bool = True,
        capture: bool = False,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:

        if self.verbose:
            print(
                "+ " + self.printable(command),
                file=sys.stderr,
            )

        try:
            return subprocess.run(
                command,
                check=check,
                text=True,
                capture_output=capture,
                timeout=timeout,
            )

        except subprocess.CalledProcessError as exc:

            details = (
                (exc.stderr or "").strip()
                or (exc.stdout or "").strip()
            )

            if not details:
                raise

            raise RuntimeError(
                "Command failed "
                f"with exit status {exc.returncode}:\n"
                f"{details}"
            ) from exc

        except subprocess.TimeoutExpired as exc:
            if check:
                raise RuntimeError(
                    f"Command timed out after {timeout} seconds: "
                    f"{self.printable(command)}"
                ) from exc
            return subprocess.CompletedProcess(
                command,
                124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"Command timed out after {timeout} seconds.\n",
            )

    def run_privileged(
        self,
        command: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:

        if os.geteuid() == 0:
            full_command = command
        else:
            full_command = [
                "sudo",
                *command,
            ]

        return self.run(
            full_command,
            check=check,
        )

    def run_as_user(
        self,
        username: str,
        command: list[str],
        *,
        check: bool = True,
        capture: bool = False,
        timeout: int | float | None = None,
    ) -> subprocess.CompletedProcess[str]:

        current_user = pwd.getpwuid(
            os.geteuid()
        ).pw_name

        if current_user == username:
            full_command = command

        elif os.geteuid() == 0:
            full_command = [
                "runuser",
                "-u",
                username,
                "--",
                *command,
            ]

        else:
            full_command = [
                "sudo",
                "-u",
                username,
                "-H",
                "--",
                *command,
            ]

        return self.run(
            full_command,
            check=check,
            capture=capture,
            timeout=timeout,
        )

    @staticmethod
    def printable(
        command: list[str],
    ) -> str:

        return " ".join(
            shlex.quote(item)
            for item in command
        )
