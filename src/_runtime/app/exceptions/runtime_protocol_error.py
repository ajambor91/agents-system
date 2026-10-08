
from typing import Any


class RuntimeProtocolError(Exception):

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Any = None,
    ):
        super().__init__(message)

        self.code = code
        self.details = details