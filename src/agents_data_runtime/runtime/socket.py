
from __future__ import annotations
import logging
from typing import Any
from lib.unix_socket import SocketClient, SocketClientBuilder, SocketConfiguration
from lib.unix_socket.exceptions.connection import UnixSocketConnectionException
from lib.configuration import Configuration

class Socket:
    _AGENTS_MANAGER = 'agents_manager'
    _METHOD_CONNECT = 'connect_agents_runtime'
    _CONNECTION_RETRIES = 10
    _TIMEOUT = 5
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
            socket_path=settings.SYSTEM_AGENT_RUNTIME_SOCKET,
            maximum_response_bytes=int(settings.MAX_MESSAGE_BYTES_BASE) * int(settings.MAX_MESSAGE_BYTES_MULTIPLIER),
            connect_timeout = 10,
            request_timeout = 30,
        )
            
        self._socket = SocketClientBuilder().create(socket_configuration).get()

    def connect(self):

        self._can_connect = True
        counter = 0
        while self._CONNECTION_RETRIES >= counter:
            if self.connected:
                return True
            if self._socket.socket_exists():
                try:
                    self._socket.connect()
                except UnixSocketConnectionException as exc:
                    if not isinstance(exc.__cause__, FileNotFoundError):
                        raise
                finally:
                    counter += 1
        if not self.connected:
            raise Exception("Could not connect to the AgentsManager")
    
    def send(self):
        if self.connected:
            return self._socket.send(module_name=self._AGENTS_MANAGER, method=self._METHOD_CONNECT)
        raise Exception("Socket not connected")