"""Expected Agents System application error."""
from .api_error import ApiError

class InputError(ApiError):
    """Invalid command contract or command-line input."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=2)
