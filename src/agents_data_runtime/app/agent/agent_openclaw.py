from typing import Any
from pathlib import Path
from ..models import MarkdownFile
from ..enums import AgentStatus
from .agent import Agent
class AgentOpenclaw(Agent):
    _DEFAULT_GATEWAY_HOST: str = "127.0.0.1"
    _DEFAULT_GATEWAY_PORT: int = 18789 
    _REQUIRED_FIELDS: list[str] = [
        "schema_version", 
        "kind", 
        "name", 
        "user", 
        "model"
    ]
    _gateway_host: str
    _gateway_port: int

    def __new__(cls, *args, **kwargs):
        if not cls._allow_creation:
            raise TypeError(
                "Cannot create agent use Agent.create()."
            )
        return super().__new__(cls)

    def __init__(self, source_dir: str,data: str):
        super().__init__(source_dir, data)


 

    def _assign_fields(self,agent_source_dir: str, data: dict[str, Any]):
        super()._assign_fields(agent_source_dir, data)
        gateway_host = data.get('gateway_host') if data.get('gateway_host') else self._DEFAULT_GATEWAY_HOST
        gateway_port = data.get('gateway_port') if data.get('gateway_port') else self._DEFAULT_GATEWAY_PORT
        self._gateway_host = gateway_host
        self._gateway_port = gateway_port
