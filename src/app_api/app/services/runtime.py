"""Runtime dispatch using the local unix-socket-client library."""
from __future__ import annotations

from shared.socket_client import RuntimeSocketGateway
from shared.socket_client import RuntimeCallError
from shared.socket_client import RuntimeUnavailableError
from lib.configuration import Configuration
from ..exceptions import ApiError


class RuntimeDispatcher:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

    def gateway(self) -> RuntimeSocketGateway:
        settings = type(self.configuration)
        return RuntimeSocketGateway(
            settings.SYSTEM_AGENT_RUNTIME_SOCKET,
            maximum_response_bytes=int(settings.MAX_MESSAGE_BYTES_BASE)
            * int(settings.MAX_MESSAGE_BYTES_MULTIPLIER),
        )

    def is_available(self) -> bool:
        try:
            self.gateway().call("configuration", "get_configuration_dict")
        except (RuntimeUnavailableError, RuntimeCallError):
            return False
        return True

    def call(self, module_name: str, method: str, arguments: dict[str, object]) -> object:
        try:
            return self.gateway().call(module_name, method, kwargs=arguments)
        except RuntimeCallError as exc:
            raise ApiError(f"Runtime: {exc}", exit_code=1) from exc
