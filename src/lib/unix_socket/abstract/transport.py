"""Abstract low-level Unix socket transport contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import SocketConfiguration


class AbstractUnixSocketTransport(ABC):
    """Own connection state and byte-level I/O for one Unix socket.

    Implementations should use ``socket.AF_UNIX``, handle partial reads and
    writes, enforce frame-size limits and translate low-level errors.
    """

    @abstractmethod
    def __init__(self) -> None:
        """Create an independent transport without opening a socket."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether this transport owns an open socket."""

    @abstractmethod
    def socket_exists(self, configuration: SocketConfiguration) -> bool:
        """Return whether the configured path currently identifies a socket."""

    @abstractmethod
    def connect(self, configuration: SocketConfiguration) -> None:
        """Open a connection using the supplied immutable configuration."""

    @abstractmethod
    def exchange(self, frame: bytes, *, timeout: float | None = None) -> bytes:
        """Write one frame and read one complete response frame."""

    @abstractmethod
    def close(self) -> None:
        """Release the socket and any transport-owned resources."""
