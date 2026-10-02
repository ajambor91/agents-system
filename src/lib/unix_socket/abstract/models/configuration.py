"""Application-owned connection settings for a Unix socket client."""

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractSocketConfiguration(ABC):
    """Expose connection data supplied by the consuming application.

    This contract neither creates configuration nor validates or serializes it.
    Concrete applications own the stored values; transports consume them.
    """

    @property
    @abstractmethod
    def socket_path(self) -> Path:
        """Filesystem path of the Unix domain socket."""

    @property
    @abstractmethod
    def connect_timeout(self) -> float | None:
        """Connection timeout in seconds; None means no timeout."""

    @property
    @abstractmethod
    def request_timeout(self) -> float | None:
        """Default response timeout in seconds; None means no timeout."""

    @property
    @abstractmethod
    def maximum_response_bytes(self) -> int:
        """Positive frame size limit in bytes, including the newline delimiter."""
