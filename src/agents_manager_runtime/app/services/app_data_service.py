import shutil

from lib.configuration import Configuration
from pathlib import Path
from lib.json_loader import JsonLoader
from typing import Any
from pathlib import Path
from ..models import MarkdownFile
from ..exceptions import AgentDataNotExists
class AppDataService:
    _configuration: Configuration

    def __init__(self, configuration: Configuration):
        self._configuration = configuration


    def is_agent_exists(self, agent_name) -> bool:
        try:
            self.get_agents_path(agent_name)
            return True
        except Exception:
            return False

    def get_agents_path(self, agent_name) -> str:
        try:
            path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
            content: dict[str, str] = JsonLoader.getJsonFileContent(path)
            agent_data = content.get(agent_name)
            if not agent_data:
                raise Exception("Cannot find agent")
            return agent_data
        except Exception as e:
            raise Exception("Agent's dir does not exist")

    def add_agent_data(self, agent_name: str,agent_path:Path) -> bool :

        path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
        existing_content: dict[str, str] = {}
        if path.is_file():
            existing_content = JsonLoader.getJsonFileContent(path)
        if existing_content.get(agent_name):
            raise Exception("Agent exists")

        existing_content[agent_name] = str(agent_path)
        return JsonLoader.save_file(existing_content, path)

    def clean_agent_data(self, agent_name: str) -> bool:
        try:
            self.remove_agent_data(agent_name)
        except AgentDataNotExists:
            pass
        except Exception as e:
            raise e
        finally:
            return True
    
    def remove_agent_data(self, agent_name: str) -> bool:
        path = Path(type(self._configuration).INSTALLED_AGENTS_LIST_PATH)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(path)
        existing_content: dict[str, str] = {}
        if not path.is_file():
            raise AgentDataNotExists("Agent does not exist")
        existing_content = JsonLoader.getJsonFileContent(path)
        if not existing_content.get(agent_name):
            raise AgentDataNotExists("Agent does not exist")
        del existing_content[agent_name] 
        JsonLoader.save_file(existing_content, path)

    def get_agent_data(self, dir_path: str) -> dict[str, Any]:
        path: Path = Path(f"{dir_path}/{type(self._configuration).AGENT_CONFIG_FILE}")
        return JsonLoader.getJsonFileContent(path)

    
    def create_source_path(self, agent_source) -> Path:
        agent_source = Path(agent_source)
        return agent_source

    def create_target_path(self, agent_name: str) -> Path:
        agent_target = Path(f"{type(self._configuration).APP_DATA_DIR}/{agent_name}")
        if agent_target.is_dir():
            raise Exception("Agent exists")
        agent_target.mkdir(parents=True, exist_ok=True)
        return agent_target


    def get_source_path(self, path: str) -> Path:
        agent_source = Path(path)
        if agent_source.is_dir():
            return agent_source
        raise  Exception("Source path does not exist")

    def copy_agents_files(
        self,
        temp_path: Path,
        target_path: Path
    ) -> bool:
        shutil.copytree(temp_path, target_path, dirs_exist_ok=True)
        return True



    def remove_data(self, path: Path) -> bool:
 
        if path and path.is_dir():
            shutil.rmtree(path)
        return True

    def load_personalities(self,agent_source: Path, personalities_dir: str) -> dict[str, MarkdownFile]:
        target_path = agent_source / personalities_dir
        raw_files = self._load_files(target_path, pattern="*.md")

        return {
            stem: MarkdownFile(**data)
            for stem, data in raw_files.items()
        }

    def _load_files(self,path: Path, pattern: str = "*.md") -> dict[str, dict[str, Any]]:
        docs: dict[str, dict[str, Any]] = {}

        if not path.is_dir():
            return docs

        for file in path.glob(pattern):
            if not file.is_file():
                continue

            stat = file.stat()
            docs[file.stem] = {
                "name": file.name,
                "path": file.resolve(),
                "content": file.read_text(encoding="utf-8"),
                "mtime": stat.st_mtime,
            }
        return docs