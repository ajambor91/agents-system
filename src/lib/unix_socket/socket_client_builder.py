"""Build independent Unix socket clients with replaceable component classes."""
from __future__ import annotations

from types import MethodType

from .abstract import (
    AbstractSocketConfiguration, AbstractUnixSocketClient,
    AbstractMessageCodec, AbstractUnixSocketTransport,
)
from .client import UnixSocketClient
from .codec import MessageCodec
from .transport import UnixSocketTransport
from .socket_client import SocketClient
from .exceptions import ClientNotConfiguredException


class _CreateMethod:
    """Bind create to a fresh default builder when accessed through the class."""

    def __init__(self, method):
        self._method = method

    def __get__(self, instance, owner):
        return MethodType(self._method, instance if instance is not None else owner.configure())


class SocketClientBuilder:
    """Keep implementation selection and the resulting client local to a builder."""

    def __init__(self, client: type[AbstractUnixSocketClient] = UnixSocketClient, codec: type[AbstractMessageCodec] = MessageCodec, transport: type[AbstractUnixSocketTransport] = UnixSocketTransport) -> None:
        self._client_factory = client
        self._codec_factory = codec
        self._transport_factory = transport
        self._socket_client: SocketClient | None = None

    @classmethod
    def configure(cls, *, client: type[AbstractUnixSocketClient] = UnixSocketClient, codec: type[AbstractMessageCodec] = MessageCodec, transport: type[AbstractUnixSocketTransport] = UnixSocketTransport) -> SocketClientBuilder:
        """Select component classes; their constructors follow the ABC contracts."""
        for implementation, contract in ((client, AbstractUnixSocketClient), (codec, AbstractMessageCodec), (transport, AbstractUnixSocketTransport)):
            if not isinstance(implementation, type) or not issubclass(implementation, contract):
                raise TypeError(f"implementation must extend {contract.__name__}")
        return cls(client, codec, transport)

    @_CreateMethod
    def create(self, configuration: AbstractSocketConfiguration) -> SocketClientBuilder:
        """Build from application settings on this builder, or a fresh default one."""
        if not isinstance(configuration, AbstractSocketConfiguration):
            raise TypeError("configuration must implement AbstractSocketConfiguration")
        if self._socket_client is not None and (self._socket_client.is_connected or self._socket_client.is_transport_connected):
            raise RuntimeError("Close the client before replacing its configuration")
        codec = self._codec_factory()
        transport = self._transport_factory()
        client = self._client_factory(configuration, codec, transport)
        self._socket_client = SocketClient(client, codec, transport)
        return self

    def get(self) -> SocketClient:
        """Return the built facade; constructing a builder never opens a socket."""
        if self._socket_client is None:
            raise ClientNotConfiguredException("Client not configured")
        return self._socket_client
