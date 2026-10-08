"""Default remote response exception."""

from ..exceptions.base import UnixSocketException


class UnixSocketResponseException(UnixSocketException):
    """Raised when the server returns a valid response describing a failure."""

    code = "unix_socket.response"

