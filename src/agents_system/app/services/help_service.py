from typing import Any
class HelpService:

    _manifests: dict[str, Any] = {}
    def __init__(self, manifests: dict[str, Any]):
        self._manifests = manifests

    def help(self, method_name: str) -> dict[str, Any]:
        print("SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS")
        print(self._manifests)
        if method_name in (None, '', 'agents_system', 'system'):
            return self._manifests
        command = next((command for command in self._manifests['commands'] if command['name'] == method_name), None)
        if command is None:
            raise ValueError(f'Unknown agent command: {method_name}')
        return {'module_name': self._manifests['module_name'], 'command': command}
        