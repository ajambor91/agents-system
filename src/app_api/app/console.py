"""Console startup and output boundary."""
from __future__ import annotations

import sys
from collections.abc import Sequence

from shared.get_config import get_config
from .application import Application
from .exceptions import ApiError
from .models import ApiResult


class Console:
    @staticmethod
    def execute(arguments: Sequence[str] | None = None, *, application: Application | None = None) -> ApiResult:
        argv = list(sys.argv[1:] if arguments is None else arguments)
        if application is not None:
            return application.run(argv)
        configuration = get_config()
        return Application(configuration).run(argv)

    @staticmethod
    def emit(result: ApiResult) -> int:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return result.exit_code

    @classmethod
    def main(cls, arguments: Sequence[str] | None = None) -> int:
        try:
            return cls.emit(cls.execute(arguments))
        except ApiError as exc:
            return cls.emit(ApiResult(exit_code=exc.exit_code, stderr=f"Błąd: {exc}\n"))
