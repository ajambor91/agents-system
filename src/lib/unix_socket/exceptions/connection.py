"""Default connection exception."""
from ..exceptions.base import UnixSocketException


class UnixSocketConnectionException(UnixSocketException):
    """Raised when the socket cannot be opened or the connection is lost."""

    code = "unix_socket.connection"

