from __future__ import annotations

from .codec import MessageCodec
from .models.configuration import SocketConfiguration
from .models.request import Request
from .models.response import Response

from .abstract import AbstractUnixSocketClient, AbstractUnixSocketTransport


class UnixSocketClient(
    AbstractUnixSocketClient[Request, Response]
):
    def __init__(
        self,
        configuration: SocketConfiguration,
        codec: MessageCodec,
        transport: AbstractUnixSocketTransport,
    ) -> None:
        self.configuration = configuration
        self.codec = codec
        self.transport = transport

    @property
    def is_connected(self) -> bool:
        return self.transport.is_connected

    def socket_exists(self) -> bool:
        return self.transport.socket_exists(self.configuration)

    def connect(self) -> None:
        print("CONNECT")
        self.transport.connect(self.configuration)

    def request(
        self,
        request: Request,
        *,
        timeout: float | None = None,
    ) -> Response:
        
        print("IN REQUEST")
        print(self.is_connected)
        frame = self.codec.encode_request(request)
        return self.codec.decode_response(
            self.transport.exchange(frame, timeout=timeout)
        )

    def close(self) -> None:
        self.transport.close()
