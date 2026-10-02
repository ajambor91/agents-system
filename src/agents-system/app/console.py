"""Console startup and output boundary."""
from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from app_api.app.exceptions import ApiError as ConsoleApiError
from shared.get_config import get_config
from .application import Application
from .exceptions import ApiError
from .models import ApiResult
from .services.command_console import CommandConsole


class Console:
    @staticmethod
    def execute(arguments: Sequence[str] | None = None, *, application: Application | None = None) -> ApiResult:
        argv = list(sys.argv[1:] if arguments is None else arguments)
        configuration = application.configuration if application is not None else get_config()
        application = application if application is not None else Application(configuration)
        return CommandConsole(configuration).run(application, argv)

    @staticmethod
    def emit(result: ApiResult) -> int:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            error = result.stderr
            if sys.stderr.isatty() and "NO_COLOR" not in os.environ:
                error = "\033[31m" + error.rstrip("\n") + "\033[0m\n"
            print(error, file=sys.stderr, end="")
        return result.exit_code

    @classmethod
    def main(cls, arguments: Sequence[str] | None = None) -> int:
        try:
            return cls.emit(cls.execute(arguments))
        except (ApiError, ConsoleApiError) as exc:
            return cls.emit(ApiResult(exit_code=exc.exit_code, stderr=f"Błąd: {exc}\n"))
        except KeyboardInterrupt:
            return cls.emit(ApiResult(exit_code=130, stderr="Błąd: przerwano przez użytkownika\n"))
        except (OSError, ValueError) as exc:
            return cls.emit(ApiResult(exit_code=1, stderr=f"Błąd systemowy: {exc}\n"))
