"""Default serialization exception."""

from ..exceptions.base import UnixSocketException


class UnixSocketSerializationException(
    UnixSocketException
    
):
    """Raised when a request cannot be encoded or a response decoded."""

    code = "unix_socket.serialization"

