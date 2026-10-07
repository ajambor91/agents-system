"""Route commands through Agents System over IPC or the selected module locally."""
from typing import Any
from lib.modules_catalog import ModulesCatalog, Module, Command, Flag
from lib.configuration import Configuration
from lib.unix_socket import SocketClient
from ..exceptions import ApiError
from .module_loader import ModuleLoader

class ModuleDispatcher:
    def __init__(self, configuration: Configuration, socket: SocketClient, catalog: ModulesCatalog) -> None:
        self.loader = ModuleLoader(configuration)
        self.socket = socket
        self.catalog = catalog

    def runtime_available(self) -> bool:
        return self.socket.is_connected and self.socket.is_healthy()

    def dispatch(self, section: Module, command: Command, arguments: list[Flag]) -> Any:
        return self._invoke(section, "execute", {
            "module_name": section.module_name,
            "method_name": command.method or command.name,
            "flags": {flag.name: flag.value for flag in arguments},
        })

    def dispatch_help(self, section: Module, method_name: str, arguments: list[Flag]) -> Any:
        return self._invoke(section, "help", {
            "module_name": section.module_name,
            "method_name": method_name,
            "flags": {flag.name: flag.value for flag in arguments},
        })

    def _invoke(self, section: Module, method: str, arguments: dict[str, Any]) -> Any:
        target = "agents_system"
        print("TESSSSSSST")
        print(method)
        try:
            if self.runtime_available():
                response = self.socket.send("agents_system", method, kwargs=arguments)
                if not response.successful:
                    raise ApiError(f"Błąd agents-system.{method}: {response.error}", exit_code=1)
                return response.result
            target = section.module_name
            action = getattr(self.loader.load(section), method, None)
            if not callable(action):
                raise ApiError(f"Moduł {target} nie udostępnia metody {method}", exit_code=1)
            local_kwargs = {"method_name": arguments["method_name"], "flags": arguments["flags"]}

            return action(**local_kwargs)
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(f"Błąd {target}.{method}: {exc}", exit_code=getattr(exc, "exit_code", 1)) from exc
