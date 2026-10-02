"""Default exception hierarchy for Unix socket clients."""

from ..exceptions.base import UnixSocketException
from ..exceptions.client_not_configured import ClientNotConfiguredException
from ..exceptions.connection import UnixSocketConnectionException
from ..exceptions.protocol import UnixSocketProtocolException
from ..exceptions.response import UnixSocketResponseException
from ..exceptions.serialization import UnixSocketSerializationException
from ..exceptions.timeout import UnixSocketTimeoutException

__all__ = [
    "ClientNotConfiguredException",
    "UnixSocketConnectionException",
    "UnixSocketException",
    "UnixSocketProtocolException",
    "UnixSocketResponseException",
    "UnixSocketSerializationException",
    "UnixSocketTimeoutException",
]

