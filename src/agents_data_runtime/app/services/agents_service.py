from .removing_service import RemovingService
from .installer_service import InstallerService
class AgentsService:
    
    _removing_service: RemovingService
    _installer_service: InstallerService
    def __init__(self, installer_service: InstallerService, removing_service: RemovingService):
        self._removing_service = removing_service
        self._installer_service = installer_service

    def install_agent(self, path: str):
        self._installer_service.install(path)

    def removing_agent(self, name: str):
        self._removing_service.remove(name)
