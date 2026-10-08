"""Missing built SocketClient facade."""

from ..exceptions.base import UnixSocketException


class ClientNotConfiguredException(UnixSocketException):
    """Raised by SocketClientBuilder.get() when no facade has been built yet."""

    code = "unix_socket.client_not_configured"

