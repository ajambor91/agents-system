"""Default protocol exception."""

from ..exceptions.base import UnixSocketException


class UnixSocketProtocolException(UnixSocketException):
    """Raised for incomplete, oversized or otherwise invalid protocol frames."""

    code = "unix_socket.protocol"

