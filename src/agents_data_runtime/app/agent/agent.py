from __future__ import annotations

from typing import Any, TYPE_CHECKING
from pathlib import Path
from ..models import MarkdownFile
from ..enums import AgentStatus
if TYPE_CHECKING:
    from ..services.loader_data_service import LoaderDataService
class Agent:
    STATUS: AgentStatus
    _PERSONALITIES_DIR = "personality"
    _DEFAULT_GATEWAY_HOST: str = "127.0.0.1"
    _DEFAULT_GATEWAY_PORT: int = 18789 
    _DEFAULT_HOME_PARENT = "/home"
    _MANIFEST_KIND: str = "agent-config"
    _SCHEMA_VERSION: int = 1
    _DEFAULT_SHELL: str = "/bin/bash"
    _REQUIRED_FIELDS: list[str] = [
        "schema_version", 
        "kind", 
        "name", 
        "user", 
        "model"
    ]
    _allow_creation = False
    _agent_name: str
    _agent_source_dir: str
    _agent_source_dir_path: Path | None = None
    _temp_path: Path | None = None
    _target_path: Path | None = None
    _model: str
    _agent_home: str
    _agent_group: str
    _shell: str
    _agent_rc: str
    _default: bool
    _gateway_host: str
    _gateway_port: int
    _tools: dict[str, Any] = {}
    _bootstrap: dict[str, Any] = {}
    _execution: dict[str, Any] = {}
    _markdown_files: dict[str, MarkdownFile] = {}
    def __new__(cls, *args, **kwargs):
        if not cls._allow_creation:
            raise TypeError(
                "Cannot create agent use Agent.create()."
            )
        return super().__new__(cls)

    def __init__(self, source_dir: str,data: str):
        self.STATUS = AgentStatus.INITIALIZED
        self._validate(data)
        self.STATUS = AgentStatus.VALIDATED
        self._assign_fields(source_dir, data)
        self.STATUS = AgentStatus.ASSIGNED

        
    @classmethod
    def create(cls, source_dir: str, data: dict[str, Any]) -> "Agent":
        try:
            cls._allow_creation = True
            instance = cls(source_dir,data)
        finally:
            cls._allow_creation = False
        return instance

    def _validate(self, data: dict[str, Any]) -> bool :
        for field in self._REQUIRED_FIELDS:
            if not data.get(field):
                raise Exception(f"Config does not contain all required fields! Field: {field}")
        return True

    def get_agent_name(self) -> str:
        return self._agent_name
    
    def get_agent_temp_path(self) -> Path:
        return self._temp_path
    
    def get_agent_target_path(self) -> Path:
        return self._target_path
    
    def get_agent_source_dir(self) -> str:
        return self._agent_source_dir

    def get_agent_source_dir_path(self)-> Path:
        return self._agent_source_dir_path

    def get_agent_home(self) -> str :
        return self._agent_home

    def get_agent_model(self) -> str:
        return self._model
    
    def update_agents_paths(self, agent_source_path: Path, agent_temp_path: Path, agent_target_path: Path):
        self._agent_source_dir_path = agent_source_path
        self._target_path = agent_target_path
        self._temp_path = agent_temp_path


    def load_md_files(self, loader_service: LoaderDataService) -> bool:
        if self.STATUS == AgentStatus.SYSTEM_INSTALLED:
            self._markdown_files = loader_service.load_personalities(self._agent_source_dir_path, self._PERSONALITIES_DIR)
        else:
            raise Exception("Agent not installed in the system")

    def _assign_fields(self,agent_source_dir: str, data: dict[str, Any]):
        self._agent_name = data.get('name')
        agent_home = data.get('home')
        self._agent_home = agent_home if data.get('home') else f"{self._DEFAULT_HOME_PARENT}/{self._agent_name}"
        agent_group = data.get('group')
        self._agent_group = agent_group if agent_group else self._agent_name
        self._default = data.get('default')
        self._model = data.get('model')
        gateway_host = data.get('gateway_host') if data.get('gateway_host') else self._DEFAULT_GATEWAY_HOST
        gateway_port = data.get('gateway_port') if data.get('gateway_port') else self._DEFAULT_GATEWAY_PORT
        self._gateway_host = gateway_host
        self._gateway_port = gateway_port
        self._agent_source_dir = agent_source_dir
        shell =  data.get("shell")
        self._shell = shell if shell else self._DEFAULT_SHELL
        if data.get('execution'):
            self._execution = data.get('execution')
        if data.get("bootstrap"):
            self._bootstrap = data.get("bootstrap")
        if data.get("tools"):
            self._tools = data.get("tools")


        


    
