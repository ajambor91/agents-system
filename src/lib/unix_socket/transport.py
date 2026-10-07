from __future__ import annotations

import socket
from pathlib import Path
from .abstract import AbstractUnixSocketTransport
from .exceptions import UnixSocketConnectionException, UnixSocketProtocolException, UnixSocketTimeoutException
from .models import SocketConfiguration

class UnixSocketTransport(AbstractUnixSocketTransport):
    def __init__(self) -> None:
        self._buffer = bytearray()
        self._socket: socket.socket | None = None
        self._configuration: SocketConfiguration | None = None

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def socket_exists(self, configuration: SocketConfiguration) -> bool:
        """Inspect the filesystem without connecting or checking server health."""
        return Path(configuration.socket_path).is_socket()

    def connect(self, configuration: SocketConfiguration) -> None:
        if configuration.maximum_response_bytes <= 0:
            raise ValueError("maximum_response_bytes must be positive")
        for value in (configuration.connect_timeout, configuration.request_timeout):
            if value is not None and value < 0:
                raise ValueError("timeouts cannot be negative")
        self.close()
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print("SOCKETPATH")
        print(configuration.socket_path)
        try:
            connection.settimeout(configuration.connect_timeout)
            connection.connect(str(configuration.socket_path))
        except socket.timeout as exc:
            connection.close()
            raise UnixSocketTimeoutException(str(exc)) from exc
        except OSError as exc:
            connection.close()
            raise UnixSocketConnectionException(str(exc)) from exc
        self._socket = connection
        self._configuration = configuration

    def exchange(self, frame: bytes, *, timeout: float | None = None) -> bytes:
        if self._socket is None or self._configuration is None:
            raise UnixSocketConnectionException("Unix socket is not connected")
        self._socket.settimeout(
            self._configuration.request_timeout if timeout is None else timeout
        )
        try:
            self._socket.sendall(frame)
            limit = self._configuration.maximum_response_bytes
            while b"\n" not in self._buffer:
                chunk = self._socket.recv(min(65536, limit + 1 - len(self._buffer)))
                if not chunk:
                    raise UnixSocketProtocolException("Socket closed before completing a response")
                self._buffer.extend(chunk)
                if b"\n" not in self._buffer and len(self._buffer) > limit:
                    raise UnixSocketProtocolException("Socket response is too large")
            end = self._buffer.index(b"\n") + 1
            if end > limit:
                raise UnixSocketProtocolException("Socket response is too large")
            frame = bytes(self._buffer[:end])
            del self._buffer[:end]
            print("EXCHANGE")
            return frame
        except UnixSocketProtocolException:
            self.close()
            raise
        except socket.timeout as exc:
            self.close()
            raise UnixSocketTimeoutException(str(exc)) from exc
        except OSError as exc:
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            print(exc)
            self.close()
            raise UnixSocketConnectionException(str(exc)) from exc

    def close(self) -> None:
        self._buffer.clear()
        if self._socket is not None:
            self._socket.close()
        self._socket = None
        self._configuration = None
