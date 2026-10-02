"""Read managed modules through the Unix socket runtime API."""
from __future__ import annotations

from typing import Any

from shared.socket_client import RuntimeSocketGateway
from shared.socket_client import RuntimeCallError
from shared.socket_client import RuntimeUnavailableError as SocketUnavailableError

from lib.configuration import Configuration
from ..exceptions import ApiError
from ..exceptions.runtime_unavailable_error import RuntimeUnavailableError


class RuntimeModulesClient:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

    def list_modules(self) -> list[dict[str, Any]]:
        settings = type(self.configuration)
        gateway = RuntimeSocketGateway(
            settings.SYSTEM_AGENT_RUNTIME_SOCKET,
            maximum_response_bytes=int(settings.MAX_MESSAGE_BYTES_BASE)
            * int(settings.MAX_MESSAGE_BYTES_MULTIPLIER),
        )
        try:
            response = gateway.call("instance-manager", "get_running_modules")
        except SocketUnavailableError as exc:
            raise RuntimeUnavailableError("Application runtime does not working") from exc
        except RuntimeCallError as exc:
            raise ApiError(f"Runtime nie działa poprawnie: {exc}") from exc
        if not isinstance(response, dict) or not isinstance(response.get("modules"), list):
            raise ApiError("Runtime zwrócił nieprawidłową listę modułów")
        modules = response["modules"]
        if any(not isinstance(module, dict) or not isinstance(module.get("name"), str) for module in modules):
            raise ApiError("Runtime zwrócił nieprawidłowy rekord modułu")
        return modules
