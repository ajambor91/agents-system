"""Stable user-facing errors raised at Agents System boundaries."""


class AgentsSystemError(RuntimeError):
    """Expected application failure rendered without a traceback."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class InputError(AgentsSystemError):
    """Invalid command contract or command-line input."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=2)


class ConfigurationError(AgentsSystemError):
    """Invalid or unavailable environment configuration."""
