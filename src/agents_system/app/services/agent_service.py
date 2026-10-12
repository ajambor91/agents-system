from __future__ import annotations
import logging
from typing import Any
from lib.unix_socket import SocketClient, SocketClientBuilder, SocketConfiguration
from lib.unix_socket.exceptions.connection import UnixSocketConnectionException
from lib.configuration import Configuration
LOGGER = logging.getLogger(__name__)
class AgentsService:
    _configuration: Configuration
    _socket: SocketClient

    def __init__(self, config: Configuration):
        self._configuration = config
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
        if self._socket.socket_exists():
            try:
                self._socket.connect()
            except UnixSocketConnectionException as exc:
                if not isinstance(exc.__cause__, FileNotFoundError):
                    raise

    def run_agent(self, agent_name: str, message: str) -> dict[str, Any]:
        print("RUN AGENT")
        res = self._socket.send(method='run_agent', kwargs={'agent_name': agent_name, 'message': message})
        print(res)
        return {
            'status': res.successful,
            'result': res.result
        }