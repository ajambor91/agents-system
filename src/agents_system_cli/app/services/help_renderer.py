"""Render module and command help returned by the application API."""
from __future__ import annotations

import json
import os
import sys
import textwrap
from typing import Any

from ..models import ApiResult
from .renderer import Renderer


class HelpRenderer:
    def __init__(self, renderer: Renderer, mode: str) -> None:
        self._renderer = renderer
        self._mode = mode
        self._color = mode == 'human' and sys.stdout.isatty() and 'NO_COLOR' not in os.environ

    def _style(self, value: str, code: str) -> str:
        return f'\033[{code}m{value}\033[0m' if self._color else value

    def _paragraph(self, value: Any, indent: str = '') -> list[str]:
        return textwrap.wrap(str(value), width=88, initial_indent=indent, subsequent_indent=indent) if value else []

    def render(self, response: Any) -> ApiResult:
        # Preserve machine-readable responses and application error messages.
        if self._mode in {'json', 'agent'} or not isinstance(response, dict) or 'message' in response:
            return self._renderer.command_result(response)
        document = response.get('command', response)
        if not isinstance(document, dict):
            return self._renderer.command_result(response)
        if 'commands' in document:
            lines = self._module(document)
        elif 'name' in document:
            lines = self._command(document)
        else:
            return self._renderer.command_result(response)
        return ApiResult(stdout='\n'.join(lines).rstrip() + '\n', data=response)

    def _module(self, document: dict[str, Any]) -> list[str]:
        section = document.get('section_name') or document.get('module_name', '')
        title = document.get('menu_name') or section
        lines = [self._style(str(title), '1;36')]
        lines.extend(self._paragraph(document.get('description')))
        lines.extend(['', self._style('Użycie', '1;35'),
                      '  ' + str(document.get('usage') or f'asystem {section} <command> [flags]'),
                      '', self._style('Komendy', '1;35')])
        commands = document.get('commands') or []
        if isinstance(commands, dict):
            commands = commands.values()
        for command in commands:
            name = str(command['name'])
            lines.append('  ' + self._style(name, '1;33'))
            lines.extend(self._paragraph(command.get('description'), '    '))
            if command.get('usage'):
                lines.append('    ' + self._style(str(command['usage']), '2'))
            lines.append('')
        lines.append(self._style(f'Pomoc komendy: asystem {section} <command> --help', '2'))
        return lines

    def _command(self, document: dict[str, Any]) -> list[str]:
        lines = [self._style(str(document['name']), '1;36')]
        lines.extend(self._paragraph(document.get('description')))
        if document.get('usage'):
            lines.extend(['', self._style('Użycie', '1;35'), '  ' + str(document['usage'])])
        flags = document.get('flags') or []
        labels = {}
        if flags:
            lines.extend(['', self._style('Flagi', '1;35')])
        for flag in flags:
            tokens = list(dict.fromkeys(token for token in
                          [flag.get('short'), flag.get('long'), *(flag.get('aliases') or [])] if token))
            label = ', '.join(tokens) or str(flag['name'])
            labels[flag['name']] = flag.get('long') or flag.get('short') or flag['name']
            if flag.get('takes_value'):
                label += ' <' + str(flag.get('type') or 'wartość') + '>'
            lines.append('  ' + self._style(label, '1;33'))
            lines.extend(self._paragraph(flag.get('description'), '    '))
            details = []
            if flag.get('required'):
                details.append('wymagana')
            if flag.get('default') is not None:
                details.append('domyślnie: ' + json.dumps(flag['default'], ensure_ascii=False))
            if details:
                lines.append('    ' + self._style(' · '.join(details), '2'))
            lines.append('')
        groups = document.get('exclusive_groups') or []
        if groups:
            lines.extend([self._style('Zasady wyboru flag', '1;35')])
            for group in groups:
                members = ', '.join(str(labels.get(name, name)) for name in group['members'])
                minimum, maximum = group.get('minimum', 0), group.get('maximum', len(group['members']))
                rule = 'Wybierz dokładnie jedną' if minimum == maximum == 1 else f'Wybierz od {minimum} do {maximum}'
                lines.extend(self._paragraph(f'{rule}: {members}.', '  '))
        if document.get('input'):
            source = document['input'].get('source')
            if source:
                lines.extend(['', self._style('Dane wejściowe', '1;35'), '  ' + str(source)])
        return lines
