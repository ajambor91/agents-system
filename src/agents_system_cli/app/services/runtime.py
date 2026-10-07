"""Runtime dispatch using the local unix-socket-client library."""
from __future__ import annotations
import logging

from lib.unix_socket import SocketClient, SocketClientBuilder, SocketConfiguration
from lib.configuration import Configuration
from ..exceptions import ApiError
LOGGER = logging.getLogger(__name__)


class RuntimeDispatcher:

    socket_client: SocketClient | None
    def __init__(self, socket_client: SocketClient) -> None:
        self.socket_client = socket_client



    def is_available(self) -> bool:
        try:
            is_healthy = self.socket_client.is_healthy()
            LOGGER.debug(f"Runtime availability check: {is_healthy}")
            return is_healthy
        except Exception as exc:
            LOGGER.error(f"Error occurred while checking runtime availability: {exc}")
            return False

    def call(self, module_name: str, method: str, arguments: dict[str, object]) -> object:
        try:
            return self.socket_client.call(module_name, method, kwargs=arguments)
        except Exception as exc:
            LOGGER.error(f"Error occurred while calling runtime: {exc}")
            raise ApiError(f"Runtime: {exc}", exit_code=1) from exc


