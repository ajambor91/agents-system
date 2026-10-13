from lib.configuration import Configuration
import shutil
import os
import sys
from pathlib import Path
class TempFilesService:
    _configuration: Configuration
    _TEMP_DIR: str = "/dev/shm/agents-system"

    def __init__(self,configuration: Configuration):
        self._configuration = configuration

    def get_temp_path(self, agent_name: str) -> Path | None:
        try:
            agent_target = Path(f"{type(self._configuration).APP_DATA_DIR}/{agent_name}")
            if agent_target.is_dir():
                return agent_target
            raise  Exception("Temp path does not exist")
        except Exception:
            return None
    def create_temp_dir(self, agent_name: str) -> Path:
        temp_path = Path(f"{self._TEMP_DIR}/{agent_name}")
        if temp_path.is_dir():
                shutil.rmtree(temp_path)
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path

    
   




        



