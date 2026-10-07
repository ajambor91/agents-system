"""Manifest-driven hierarchical console application."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
import time
import asyncio
from .exceptions import ApiError
from .models import ApiResult
from .services import ModuleDispatcher
from .services import Renderer
from .services import FlagParser
from .services import ConsoleArgumentParser
from .services import InteractiveConsole
from .services import RuntimeStatusRenderer
from lib.configuration import Configuration
from lib.modules_catalog import ModulesCatalog, ModulesFactory, Module, Flag
from .services import RenderersFactory
from lib.unix_socket import SocketClient, SocketClientBuilder, SocketConfiguration
from lib.unix_socket.exceptions import UnixSocketConnectionException
class AgentsSystemCLI:

    renderers_factory: RenderersFactory | None = None
    dispatcher: ModuleDispatcher | None = None
    catalog: ModulesCatalog | None = None
    socket_client: SocketClient
    # selected_command: Command | None = None
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        self.__initialize()

    def runtime_available(self) -> bool:
        # return False
        # return self.dispatcher.runtime_available
        return self.socket_client.is_connected and self.socket_client.is_healthy()

    def run(self, arguments: Sequence[str]) -> ApiResult:
        mode = "human"
        help: bool = False
        try:
            help_flag: Flag | None = None
            options = ConsoleArgumentParser.parse(self.catalog, arguments)
            mode = options.mode
            remaining = options.remaining
        #     if mode == "interactive":
        #         return InteractiveConsole().run(self, manifest)
            renderer = self.renderers_factory.create_renderer(mode);
            if not remaining:
                return self.renderers_factory.create_status_renderer(mode, renderer).prepend(renderer.root_help(self.catalog))
            module_name = remaining.pop(0)
            module: Module = None

            if module_name in self.catalog.modules:
                module = self.catalog.modules[module_name]

            elif module_name in self.catalog.modules_by_section:
                module = self.catalog.modules_by_section[module_name]

            else:
                raise ApiError(f"Nieznana sekcja: {module_name}")
            if not remaining:
                help = True
                response = self.dispatcher.dispatch_help(module, module_name, [])
            else:
                command_name = remaining.pop(0)
                command = module.commands.get(command_name)
                if command is None:
                    raise ApiError(f"Nieznana komenda w sekcji {module.module_name}: {command_name}")
                if options.help_requested or not remaining:
                    help = True
                    from dataclasses import replace
                    help_command = replace(command, flags=[replace(flag, required=False) for flag in command.flags])
                    flags = FlagParser.parse(help_command, remaining)
                    response = self.dispatcher.dispatch_help(module, command.method or command.name, flags)
                else:
                    flags = FlagParser.parse(command, remaining)
                    response = self.dispatcher.dispatch(module, command, flags)
            if help:
                return self.renderers_factory.create_help_renderer(mode, renderer).render(response)
            return renderer.command_result(response)
        except ApiError as exc:
            return self.renderers_factory.create_renderer("human-raw" if mode == "interactive" else mode).error(str(exc), exc.exit_code)
            # return Renderer("human-raw" if mode == "interactive" else mode).error(str(exc), exc.exit_code)
        except KeyboardInterrupt:
            return self.renderers_factory.create_renderer("human-raw" if mode == "interactive" else mode).error(
                "przerwano przez użytkownika",
                130,
            )
            # return Renderer("human-raw" if mode == "interactive" else mode).error(
            #     "przerwano przez użytkownika",
            #     130,
            # )


    def run_dict(self, arguments: Sequence[str]) -> dict[str, Any]:
        """Run through runtime and return a JSON-serializable result."""
        return self.run(arguments).to_dict()

    def __initialize(self) -> None:
        """Initialize the application, loading manifests and preparing the runtime."""
        settings = type(self.configuration)
        socket_configuration = SocketConfiguration(
            socket_path=settings.SYSTEM_AGENT_RUNTIME_SOCKET,
            maximum_response_bytes=int(settings.MAX_MESSAGE_BYTES_BASE)
            * int(settings.MAX_MESSAGE_BYTES_MULTIPLIER),
            connect_timeout = 10,
            request_timeout = 30,

        )

        self.socket_client = SocketClientBuilder().create(socket_configuration).get()
        if self.socket_client.socket_exists():
            try:
                self.socket_client.connect()
            except UnixSocketConnectionException as exc:
                # The socket may disappear between the filesystem check and connect.
                if not isinstance(exc.__cause__, FileNotFoundError):
                    raise

        self.catalog = ModulesFactory.create_modules_from_json_file(Path(type(self.configuration).MODULES_MANIFEST_PATH))
        self.dispatcher = ModuleDispatcher(self.configuration, self.socket_client, self.catalog)
        self.renderers_factory = RenderersFactory(self.configuration, self.runtime_available)



        
