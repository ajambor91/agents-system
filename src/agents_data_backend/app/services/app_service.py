from typing import Any
from .agent_service import AgentsService
from lib.configuration import Configuration
from ..socket import Socket
import logging
LOGGER = logging.getLogger(__name__)

class AppService:

    _agents_service: AgentsService
    _socket: Socket

    def __init__(self, configuration: Configuration):
        self._socket = Socket(configuration)
        self._agents_service = AgentsService(socket=self._socket)



    def exec( 
            self,
            method_name: str,
            flags: dict[str, Any] | None = None
        ) -> dict[str, Any]:
        try:
            action = getattr(self, method_name, None)
            if not action or not callable(action):
                raise Exception("Cannot find requested action: %s", method_name)
            result = action(flags)
            if not isinstance(result, dict):
                raise Exception("Requested action returns uknown type")
            return result
        except Exception as e:
            LOGGER.error({
                "status": "Failed",
                "action": method_name,
                "details": e 
            })
            return {
                "Status": "failed",
                "details": e
            }

    def run(self, args: dict[str,Any] = {}):
        LOGGER.debug("Received request for run agent")
        agent_name = args.get('name') 
        message = args.get('message')
        if not agent_name or not message:
            raise Exception("Agent name and message are required while running agent")
        return self._agents_service.run_agent(agent_name=agent_name, message=message)

    def install(self, args: dict[str,Any] = {}) -> dict[str, Any]:
        try:
            path = args.get('path')
            if not path:
                raise Exception("Agent must have source dir path!") 
            LOGGER.debug("Received request to install agent from path: %s", path)

            name = args.get('name')
            user = args.get('user')
            model = args.get('model')
            dry_run = args.get('dry_run')
            force = args.get('force')
            return self._agents_service.install_agent(path, name, user, model, dry_run, force)
        except Exception as exc:
            return {
                "Status": "install-error",
                "details":  getattr(exc, "details", str(exc))                           
            }
    def delete(self, args: dict[str,Any] = {}) -> dict[str, Any]:
        try:
            name = args.get('name')
            if not name:
                raise Exception("Agent must have a name!") 

            LOGGER.debug("Received request to delete agent with name: %s", name)
            dry_run = args.get('dry_run')
            force = args.get('force')
            return self._agents_service.delete_agent(name, dry_run, force)
        except Exception as exc:
            return {
                "Status": "delete-error",
                "details":  getattr(exc, "details", str(exc))                           
            }
    def connect_agents_runtime(self) -> dict[str, Any]:
        try:
            LOGGER.debug("Received request for connect to the agents-manager")
            self._socket.connect()
            is_connected = self._socket.connected
            if not is_connected:
                raise Exception("Cannot connect to the Agents Runtime Socket")
            return {"Status": "connected"}
        except Exception as exc:
            return {
                "Status": "disconnected",
                "details":  getattr(exc, "details", str(exc))                           
            }

        
