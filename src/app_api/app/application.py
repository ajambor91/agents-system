"""Manifest-driven hierarchical console application."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .exceptions import ApiError
from .models import ApiResult
from .services.module_dispatcher import ModuleDispatcher
from .services.manifests import ManifestCatalog, find_command
from .services.renderer import Renderer
from .services.flag_parser import FlagParser
from .services.console_argument_parser import ConsoleArgumentParser
from .services.interactive_console import InteractiveConsole
from .services.runtime_status_renderer import RuntimeStatusRenderer
from lib.configuration import Configuration


class Application:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration
        settings = type(configuration)
        self.repository_root = Path(settings.APP_DIR).expanduser().resolve()
        rendered_manifest = (
            self.repository_root / "resources" / "agents-system.module.json"
        )
        template_manifest = (
            self.repository_root / "resources" / "agents-system.module.template.json"
        )
        configured_manifest = Path(settings.MODULES_MANIFEST_PATH).expanduser()
        manifest_path = (
            configured_manifest
            if configured_manifest.is_file()
            else rendered_manifest
            if rendered_manifest.is_file()
            else template_manifest
        )
        self.catalog = ManifestCatalog(manifest_path)
        self.dispatcher = ModuleDispatcher(configuration)

    @property
    def runtime_available(self) -> bool:
        return self.dispatcher.runtime_available

    def run(self, arguments: Sequence[str]) -> ApiResult:
        mode = "human"
        try:
            manifest = self.catalog.load()
            options = ConsoleArgumentParser.parse(manifest, arguments)
            mode = options.mode
            remaining = options.remaining
            if mode == "interactive":
                return InteractiveConsole().run(self, manifest)
            renderer = Renderer(mode)
            if not remaining:
                return RuntimeStatusRenderer.prepend(renderer.root_help(manifest), mode, runtime_available=self.runtime_available)
            section_name = remaining.pop(0)
            section = manifest["sections"].get(section_name)
            if section is None:
                raise ApiError(f"Nieznana sekcja: {section_name}")
            if not remaining:
                return RuntimeStatusRenderer.prepend(renderer.section_help(section_name, section), mode, runtime_available=self.runtime_available)
            command_name = remaining.pop(0)
            command = find_command(section, command_name)
            if command is None:
                raise ApiError(f"Nieznana komenda w sekcji {section_name}: {command_name}")
            if options.help_requested:
                return RuntimeStatusRenderer.prepend(renderer.command_help(section_name, command), mode, runtime_available=self.runtime_available)
            arguments_map = FlagParser.parse(command, remaining)
            response = self.dispatcher.dispatch(section, command, arguments_map)
            return renderer.command_result(response)
        except ApiError as exc:
            return Renderer("human-raw" if mode == "interactive" else mode).error(str(exc), exc.exit_code)
        except KeyboardInterrupt:
            return Renderer("human-raw" if mode == "interactive" else mode).error(
                "przerwano przez użytkownika",
                130,
            )

    def run_dict(self, arguments: Sequence[str]) -> dict[str, Any]:
        """Run through runtime and return a JSON-serializable result."""
        return self.run(arguments).to_dict()
