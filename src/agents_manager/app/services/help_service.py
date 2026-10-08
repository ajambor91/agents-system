"""Return manifest help without presentation or runtime side effects."""
from __future__ import annotations

from typing import Any


class HelpService:
    def __init__(self, manifests: dict[str, Any]) -> None:
        self._manifests = manifests

    def help(self, method_name: str | None = None) -> dict[str, Any]:
        try:
            if method_name in (None, '', 'agents', 'agents_manager'):
                return self._manifests
            command = next(
                (command for command in self._manifests.get('commands', [])
                 if command['name'] == method_name),
                None,
            )
            if command is None:
                return {'message': 'Method not found'}
            return {'module_name': self._manifests['module_name'], 'command': command}
        except Exception as exc:
            return {'message': str(exc)}
