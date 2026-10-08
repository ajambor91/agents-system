from .removing_service import RemovingService
from .installer_service import InstallerService
from ..models import AgentDTO
from ..enums import AgentStatus
from typing import Any
class AgentsService:
    
    _removing_service: RemovingService
    _installer_service: InstallerService
    def __init__(self, installer_service: InstallerService, removing_service: RemovingService):
        self._removing_service = removing_service
        self._installer_service = installer_service

    def install_agent(self, path: str, force: bool) -> dict[str, Any]:
        agent: AgentDTO  = self._installer_service.install(path, force)
        if agent.status == AgentStatus.INSTALLING_INSTALLATION_ERROR:
            return self._cleanup(agent)
        elif agent.status == AgentStatus.INSTALLING_INSTALLED:
            return {
                "status": "Agent was installed",
                "details" :agent.to_dict()
            }
        else:
            return {
                "status" : "Agent could not be installed",
                "details" : agent.to_dict()
                } 
        
    def removing_agent(self, name: str) -> dict[str, Any]:
        agent_dto: AgentDTO = self._removing_service.remove(name)
        if agent_dto.status == AgentStatus.REMOVING_REMOVED:
            return {
                "status": "Agent was removed",
                "details": agent_dto.to_dict()
            }
        elif agent_dto.status == AgentStatus.REMVIGN_REMOVED_ERROR:
            return {
                    "status": "Agent could not be removed",
                    "details" :agent_dto.to_dict()
                }
        else:
            return {
                        "status" : "Agent could not be removed",
                        "details" : agent_dto.to_dict()
                    } 

    def _cleanup(self, agent: AgentDTO) -> dict[str, Any]:
        agent_dto: AgentDTO  = self._removing_service.cleanup(agent)
        if agent_dto.status == AgentStatus.CLEANING_ERROR:
            return {
                        "status": "Agent could not be installed; clean up failed.",
                        "details": agent_dto.to_dict()
                    }
        elif agent_dto.status == AgentStatus.CLEANING_CLEANED:
            return {
                            "status": "Agent could not be installed, clean up success",
                            "details" :agent_dto.to_dict()
                }
        else:
            return {
                        "status" : " could not be installed; clran up failed.",
                        "details" : "Unknown error"
                    } 