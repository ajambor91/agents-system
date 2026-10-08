"""Application-owned connection settings for a Unix socket client."""

from pathlib import Path


class SocketConfiguration:
    """Expose connection data supplied by the consuming application.

    This contract neither creates configuration nor validates or serializes it.
    Concrete applications own the stored values; transports consume them.
    """
    def __init__(self, socket_path: Path, connect_timeout: float | None, request_timeout: float | None, maximum_response_bytes: int):
        self._socket_path = socket_path
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._maximum_response_bytes = maximum_response_bytes

    @property
    def socket_path(self) -> Path:
        """Return the configured Unix socket path."""
        return self._socket_path
    @property
    def connect_timeout(self) -> float | None:
        """Connection timeout in seconds; None means no timeout."""
        return self._connect_timeout

    @property
    def request_timeout(self) -> float | None:
        """Default response timeout in seconds; None means no timeout."""
        return self._request_timeout

    @property
    def maximum_response_bytes(self) -> int:
        """Positive frame size limit in bytes, including the newline delimiter."""
        return self._maximum_response_bytes
