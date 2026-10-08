from typing import Any

class RuntimeDispatchError(RuntimeError):

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Any = None,
    ) -> None:
        super().__init__(message)

        self.code = code
        self.details = details