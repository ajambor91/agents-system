"""Adapt standalone arguments to the same manifest contract as app_api."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app_api.app.services.console_argument_parser import ConsoleArgumentParser
from app_api.app.services.flag_parser import FlagParser
from app_api.app.services.manifests import ManifestCatalog, find_command
from app_api.app.services.renderer import Renderer
from lib.configuration import Configuration
from ..application import Application
from ..exceptions import InputError
from ..models import ApiResult


class CommandConsole:
    def __init__(self, configuration: Configuration) -> None:
        settings = type(configuration)
        configured = Path(settings.MODULES_MANIFEST_PATH).expanduser()
        repository = Path(settings.APP_DIR).expanduser().resolve()
        rendered = repository / "resources" / "agents-system.module.json"
        template = repository / "resources" / "agents-system.module.template.json"
        self.catalog = ManifestCatalog(configured if configured.is_file() else rendered if rendered.is_file() else template)

    def run(self, application: Application, arguments: Sequence[str]) -> ApiResult:
        manifest = self.catalog.load()
        section_name = next((name for name, section in manifest["sections"].items() if section["module_name"] == "agents-system"), None)
        if section_name is None:
            raise InputError("Manifest nie udostępnia sekcji agents-system")
        options = ConsoleArgumentParser.parse(manifest, [section_name, *arguments])
        if options.mode == "interactive":
            raise InputError("Tryb interaktywny jest dostępny przez asystem --interactive")
        renderer = Renderer(options.mode)
        section = manifest["sections"][section_name]
        argv = options.remaining[1:]
        if not argv:
            result = renderer.section_help(section_name, section)
        else:
            command = find_command(section, argv[0])
            if command is None:
                raise InputError(f"Nieznana komenda: {argv[0]}")
            if options.help_requested:
                result = renderer.command_help(section_name, command)
            else:
                values = FlagParser.parse(command, argv[1:])
                method = command.get("method", command["name"].replace("-", "_"))
                action = getattr(application, method, None)
                if not callable(action):
                    raise InputError(f"Aplikacja nie udostępnia metody {method}")
                result = renderer.command_result(action(**values))
        return ApiResult(**result.to_dict())
