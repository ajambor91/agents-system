"""Read and render versioned lifecycle help documents."""
import json
from pathlib import Path
from typing import Any
from ..errors import InstallationError


def read_help(path: Path, operation: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise InstallationError(f'Nie można odczytać pomocy: {path}: {exc}') from exc
    if (not isinstance(document, dict) or document.get('schema_version') != 1
            or document.get('kind') != 'installer-help' or document.get('operation') != operation):
        raise InstallationError(f'Nieprawidłowy manifest pomocy: {path}')
    for field in ('command', 'description', 'usage'):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise InstallationError(f'Brak {field} w pomocy: {path}')
    flags = document.get('flags')
    if not isinstance(flags, list):
        raise InstallationError(f'Brak flags w pomocy: {path}')
    for flag in flags:
        if not isinstance(flag, dict) or not isinstance(flag.get('description'), str):
            raise InstallationError(f'Nieprawidłowa flaga w pomocy: {path}')
    return document


def render_help(document: dict[str, Any]) -> str:
    lines = [document['command'], document['description'], '', 'Użycie:', '  ' + document['usage'], '', 'Opcje:']
    for flag in document['flags']:
        tokens = [item for item in (flag.get('short'), flag.get('long'), *flag.get('aliases', [])) if item]
        suffix = ' VALUE' if flag.get('takes_value') else ''
        required = ' (wymagana)' if flag.get('required') else ''
        lines.append(f"  {', '.join(tokens) + suffix:<32} {flag['description']}{required}")
    return '\n'.join(lines) + '\n'
