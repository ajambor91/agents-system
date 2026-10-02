from __future__ import annotations

from lib.unix_socket.codec import MessageCodec
from lib.unix_socket.models.request import Request
from lib.unix_socket.models.response import Response

from .abstract import AbstractUnixSocketClient, AbstractUnixSocketTransport, AbstractSocketConfiguration


class UnixSocketClient(
    AbstractUnixSocketClient[Request, Response]
):
    def __init__(
        self,
        configuration: AbstractSocketConfiguration,
        codec: MessageCodec,
        transport: AbstractUnixSocketTransport,
    ) -> None:
        self.configuration = configuration
        self.codec = codec
        self.transport = transport

    @property
    def is_connected(self) -> bool:
        return self.transport.is_connected

    def connect(self) -> None:
        self.transport.connect(self.configuration)

    def request(
        self,
        request: Request,
        *,
        timeout: float | None = None,
    ) -> Response:
        frame = self.codec.encode_request(request)
        return self.codec.decode_response(
            self.transport.exchange(frame, timeout=timeout)
        )

    def close(self) -> None:
        self.transport.close()
