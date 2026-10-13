
from __future__ import annotations
import logging
from typing import Any
from lib.unix_socket import SocketClient, SocketClientBuilder, SocketConfiguration
from lib.unix_socket.exceptions.connection import UnixSocketConnectionException
from lib.configuration import Configuration

class Socket:
    _configuration: Configuration
    _socket: SocketClient
    _can_connect: bool

    @property
    def connected(self) -> bool:
        return self._can_connect and self._socket.is_connected
    
    def __init__(self, config: Configuration):
          self._configuration = config
          self._can_connect = False
          self._initialize()


    def _initialize(self) -> None:
        settings = type(self._configuration)
        socket_configuration = SocketConfiguration(
            socket_path=settings.SYSTEM_AGENT_MANAGER_RUNTIME_SOCKET,
            maximum_response_bytes=int(settings.MAX_MESSAGE_BYTES_BASE) * int(settings.MAX_MESSAGE_BYTES_MULTIPLIER),
            connect_timeout = 10,
            request_timeout = 30,
        )
            
        self._socket = SocketClientBuilder().create(socket_configuration).get()

    def connect(self):
        self._can_connect = True
        if self._socket.socket_exists():
            try:
                self._socket.connect()
            except UnixSocketConnectionException as exc:
                if not isinstance(exc.__cause__, FileNotFoundError):
                    raise
         
    
    def send(self, method_name: str, kwargs: dict[str, Any]):
        if self.connected:
            return self._socket.send(method=method_name, kwargs=kwargs)
        raise Exception("Socket not connected")