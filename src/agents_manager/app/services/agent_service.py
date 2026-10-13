from __future__ import annotations
import logging
from typing import Any
from ..socket import Socket
LOGGER = logging.getLogger(__name__)
class AgentsService:
    _socket: Socket
    def __init__(self, socket: Socket):
        self._socket = socket

    def run_agent(self, agent_name: str, message: str) -> dict[str, Any]:
        LOGGER.info("Sending run_agent request with agent_name: %s, message: %s", agent_name, message)
        res = self._socket.send(method_name='run_agent', kwargs={'agent_name': agent_name, 'message': message})
        LOGGER.info("run_agent request with agent_name: %s, message: %s was sent", agent_name, message)

        return {
            'status': res.successful,
            'result': res.result
        }
    
    def install_agent(self, path: str, name: str = None, user: str = None, model: str = None, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
        LOGGER.info("Sending install_agent request with path: %s, user: %s, model: %s", path, user, model)
        res = self._socket.send(method_name='install_agent', kwargs={'path': path, 'agent_name': name, 'user': user, 'model': model, 'dry_run': dry_run, 'force': force})
        LOGGER.info("install_agent request with path: %s, user: %s, model: %s was sent", path, user, model)

        return {
            'status': res.successful,
            'result': res.result
        }

    def delete_agent(self, name: str, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
        LOGGER.info("Sending delete_agent request with name: %s", name)
        res = self._socket.send(method_name='remove_agent', kwargs={'agent_name': name, 'dry_run': dry_run, 'force': force})
        LOGGER.info("delete_agent request with name: %s was sent", name)

        return {
            'status': res.successful,
            'result': res.result
        }

    def list_agents(self) -> dict[str, Any]:
        pass

    def update_agent(self) -> dict[str, Any]:
        pass