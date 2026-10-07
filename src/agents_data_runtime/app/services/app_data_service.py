from lib.configuration import Configuration
from pathlib import Path
from lib.json_loader import JsonLoader
from typing import Any
class AppDataService:

    _configuration: Configuration

    def __init__(self, configuration: Configuration):
        self._configuration = configuration

    def get_agents_path(self, agent_name) -> str:
        path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
        content: dict[str, str] = JsonLoader.getJsonFileContent(path)
        agent_data = content.get(agent_name)
        if not agent_data:
            raise Exception("Cannot find agent")
        return agent_data

    def add_agent_data(self, agent_name: str,agent_path:str) -> bool :

        path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
        existing_content: dict[str, Any] = {}
        if path.is_file():
            existing_content = JsonLoader.getJsonFileContent(path)
        if existing_content.get(agent_name):
            raise Exception("Agent exists")

        existing_content[agent_name] = agent_path
        return JsonLoader.save_file(existing_content, path)
    
    def remove_agent_data(agent_name: str) -> bool:
        path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
        existing_content: dict[str, Any] = {}
        if not path.is_file():
            raise Exception("Agent does not exist")
        existing_content = JsonLoader.getJsonFileContent(path)
        if not existing_content.get(agent_name):
            raise Exception("Agent exists")
        del existing_content[agent_name] 

