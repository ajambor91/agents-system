"""Application-facing facade for Unix socket client components."""

from __future__ import annotations

from typing import cast

from .abstract import (
    AbstractMessageCodec,
    AbstractSocketConfiguration,
    AbstractUnixSocketClient,
    AbstractUnixSocketTransport,
)

from .models import Request, Response

class SocketClient:
    """Delegate connection, message, codec and transport operations.

    Construct through SocketClientBuilder.create(configuration).get().
    """

    def __init__(self, client: AbstractUnixSocketClient, codec: AbstractMessageCodec, transport: AbstractUnixSocketTransport) -> None:
        self._client = client
        self._codec = codec
        self._transport = transport

    def message(self, request: Request, *, timeout: float | None = None) -> Response:
        return self.request(request, timeout=timeout)

    @property
    def client(self) -> AbstractUnixSocketClient:
        """Return the configured high-level client implementation."""
        return self._client

    @property
    def codec(self) -> AbstractMessageCodec:
        """Return the configured message codec implementation."""
        return self._codec

    @property
    def transport(self) -> AbstractUnixSocketTransport:
        """Return the configured low-level transport implementation."""
        return self._transport

    @property
    def is_connected(self) -> bool:
        """Delegate connection state to the high-level client."""
        return self._client.is_connected

    @property
    def is_transport_connected(self) -> bool:
        """Delegate connection state to the low-level transport."""
        return self._transport.is_connected

    def connect(self) -> SocketClient:
        """Connect the configured high-level client and return this facade."""
        self._client.connect()
        return self

    def request(
        self,
        request: Request,
        *,
        timeout: float | None = None,
    ) -> Response:
        """Send a typed request through the configured high-level client."""
        return cast(Response, self._client.request(request, timeout=timeout))

    def close(self) -> SocketClient:
        """Close the configured high-level client and return this facade."""
        self._client.close()
        return self

    def encode_request(self, request: Request) -> bytes:
        """Encode a request with the configured codec."""
        return self._codec.encode_request(request)

    def decode_response(self, frame: bytes) -> Response:
        """Decode a response frame with the configured codec."""
        return cast(Response, self._codec.decode_response(frame))

    def connect_transport(self, configuration: AbstractSocketConfiguration) -> SocketClient:
        """Connect the configured transport and return this facade."""
        self._transport.connect(configuration)
        return self

    def exchange(self, frame: bytes, *, timeout: float | None = None) -> bytes:
        """Exchange a raw frame through the configured transport."""
        return self._transport.exchange(frame, timeout=timeout)

    def close_transport(self) -> SocketClient:
        """Close the configured transport and return this facade."""
        self._transport.close()
        return self

