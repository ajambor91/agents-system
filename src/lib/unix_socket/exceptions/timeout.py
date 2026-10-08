"""Default timeout exception."""

from ..exceptions.base import UnixSocketException


class UnixSocketTimeoutException(UnixSocketException):
    """Raised when connecting, writing or reading exceeds its deadline."""

    code = "unix_socket.timeout"

