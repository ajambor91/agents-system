from lib.configuration import Configuration
from lib.json_loader import JsonLoader
from typing import Any
from pathlib import Path
from ..models import MarkdownFile
class LoaderDataService:
    _configuration: Configuration

    def __init__(self,configuration: Configuration):
        self._configuration = configuration

    def get_agent_data(self, dir_path: str) -> dict[str, Any]:
        path: Path = Path(f"{dir_path}/{type(self._configuration).AGENT_CONFIG_FILE}")
        return JsonLoader.getJsonFileContent(path)
        

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


    def load_personalities(self,agent_source: Path, personalities_dir: str) -> dict[str, MarkdownFile]:
        target_path = agent_source / personalities_dir
        raw_files = self._load_files(target_path, pattern="*.md")

        return {
            stem: MarkdownFile(**data)
            for stem, data in raw_files.items()
        }

