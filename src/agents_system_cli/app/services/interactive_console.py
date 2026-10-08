"""Terminal session for the public application API."""

import logging

import shlex
import sys
from typing import Any
from ..exceptions import ApiError
from ..models import ApiResult
from . import Renderer


LOGGER = logging.getLogger(__name__)


class InteractiveConsole:
    def run(self, application, manifest: dict[str, Any]) -> ApiResult:
        LOGGER.debug('Starting interactive_console.run')
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ApiError("Tryb --interactive wymaga terminala")
        current_section: str | None = None
        renderer = Renderer("human")
        print(renderer.runtime_status(application.runtime_available) + renderer.root_help(manifest).stdout, end="")
        while True:
            prompt = f"asystem/{current_section or ''}> "
            try:
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return ApiResult()
            if not line:
                continue
            if line in {"q", "quit", "exit"}:
                return ApiResult()
            if line in {"b", "back"}:
                current_section = None
                print(renderer.runtime_status(application.runtime_available) + renderer.root_help(manifest).stdout, end="")
                continue
            tokens = shlex.split(line)
            if current_section is None and tokens[0] in manifest["sections"]:
                current_section = tokens.pop(0)
                if not tokens:
                    print(renderer.runtime_status(application.runtime_available) + renderer.section_help(current_section, manifest["sections"][current_section]).stdout, end="")
                    continue
            nested = ["--human"] + ([current_section] if current_section else []) + tokens
            result = application.run(nested)
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
