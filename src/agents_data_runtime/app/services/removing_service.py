from .system_service import SystemService
from .temp_files_service import TempFilesService
from .app_data_service import AppDataService
from ..agent import AgentOpenclaw, Agent
from ..ports import AgentRuntimeRemove
from ..ports.agent_runtime_install import AgentRuntimeInstall
from ..enums import AgentStatus
from ..models import AgentDTO
class RemovingService:
    _temp_service: TempFilesService
    _system_service: SystemService
    _agents_runtime: AgentRuntimeRemove
    _app_data_service: AppDataService

    def __init__(self, temp_service: TempFilesService, system_service: SystemService, agent_runtime: AgentRuntimeInstall, app_data: AppDataService):
        self._temp_service = temp_service
        self._system_service = system_service
        self._agents_runtime = agent_runtime
        self._app_data_service = app_data

    def remove(self, name: str) -> AgentDTO:
        agent: Agent = None
        status = AgentStatus.REMOVING_INITIALIZED
        try:
            agent_path = self._app_data_service.get_agents_path(name)
            
            status = AgentStatus.REMOVING_GET_AGENT_PATH
            agent_config = self._app_data_service.get_agent_data(agent_path)
            status = AgentStatus.REMOVING_GET_AGENT_DATA
            agent = AgentOpenclaw.create(agent_path, agent_config)
            temp_path = self._temp_service.get_temp_path(agent.get_agent_name())
            source_path = self._app_data_service.get_source_path(agent_path)
            agent.update_agents_paths(agent_temp_path=temp_path, agent_source_path=source_path)
            agent.update_status(AgentStatus.REMOVING_CREATED)
            self._system_service.remove_agent_user(agent.get_agent_name())
            agent.update_status(AgentStatus.REMOVING_REMOVE_USER)
            self._agents_runtime.remove_agent(agent.get_agent_name())
            agent.update_status(AgentStatus.REMOVING_REMOVE_AGENT)
            self._app_data_service.remove_data(agent.get_agent_source_dir_path())
            agent.update_status(AgentStatus.REMOVING_REMOVE_TARGET)
            self._app_data_service.remove_data(agent.get_agent_temp_path())
            agent.update_status(AgentStatus.REMOVING_REMOVE_TEMP)
            self._app_data_service.remove_agent_data(agent.get_agent_name())
            agent.update_status(AgentStatus.REMOVING_REMOVE_ENTRY)
            return AgentDTO(
                status=AgentStatus.REMOVING_REMOVED,
                name=agent.get_agent_name(),
                home=agent.get_home_path(),
                group=agent.get_agent_group(),
                shell=agent.get_agent_shell(),
                source_dir_path=agent.get_agent_source_dir_path(),
                temp_path=agent.get_agent_temp_path(),
                target_path=agent.get_agent_target_path(),
                exceptions=None
                )
        except Exception as e:

            if isinstance(agent,Agent):
                status = agent.get_status() if agent.get_status() else status
                return AgentDTO(
                    status=AgentStatus.REMVIGN_REMOVED_ERROR,
                    break_status=status,
                    name=agent.get_agent_name(),
                    home=agent.get_home_path(),
                    group=agent.get_agent_group(),
                    shell=agent.get_agent_shell(),
                    source_dir_path=agent.get_agent_source_dir_path(),
                    temp_path=agent.get_agent_temp_path(),
                    target_path=agent.get_agent_target_path(),
                    exceptions= {'removing': e}
                )
            return AgentDTO(
                    status=AgentStatus.REMVIGN_REMOVED_ERROR,
                    break_status=status,
                    exceptions= {'removing': e}
                )

    def cleanup(self, agent: AgentDTO) -> AgentDTO:
        cleaning = self._check_is_cleaning_needed(agent)
        print("CCCC")
        print(cleaning)
        try:
            if not cleaning:
                print("NO CLEAR")
                return self._return_without_cleaning(agent)
            return self._cleaning(agent)
            
        except Exception as e:
            return AgentDTO(
                    status=AgentStatus.CLEANING_ERROR,
                    break_status=agent.break_status,
                    clean_status=status,
                    name=agent.name,
                    home=agent.home,
                    group=agent.group,
                    shell=agent.shell,
                    source_dir_path=agent.source_dir_path,
                    temp_path=agent.temp_path,
                    target_path=agent.target_path,
                    exceptions={'installation': agent.exceptions['installation'], 'cleaning': e}
                )


    def _cleaning(self, agent: AgentDTO) -> AgentDTO:
        status = AgentStatus.CLEANING_INITIALIZED
        statuses: list[AgentStatus] = list(AgentStatus)
        statuses.reverse()
        status_index = statuses.index(agent.break_status)
        steps_to_clean: list[AgentStatus] = statuses[status_index:]
        for status in steps_to_clean:
            if status in [
                AgentStatus.INSTALLING_CREATED_TEMP_DIR,
                AgentStatus.INSTALLING_CREATED_TARGET_DIR,
                AgentStatus.INSTALLING_COPIED_TEMP,
                AgentStatus.INSTALLING_USER_CREATED,
                AgentStatus.INSTALLING_AGENBT_RUNTIME_INSTALLED,
                AgentStatus.INSTALLING_COPIED_DATA_FILES,
                AgentStatus.INSTALLING_INITIALIZED
                ]:
                continue
            match status:
                case  AgentStatus.INSTALLING_CREATED_TEMP_DIR:
                    self._system_service.remove_data(agent.temp_path)
                case  AgentStatus.INSTALLING_CREATED_TARGET_DIR:
                    self._system_service.remove_data(agent.target_path)
                    status = AgentStatus.CLEANING_CLEANED_TARGET     
                case AgentStatus.INSTALLING_USER_CREATED:
                    self._system_service.remove_agent_user(agent.name)
                    status = AgentStatus.CLEANING_CLEANED_USER
                case AgentStatus.INSTALLING_AGENBT_RUNTIME_INSTALLED:
                    self._agents_runtime.remove_agent(agent.name)
                    status = AgentStatus.CLEANING_CLEANED_AGENT
                case AgentStatus.INSTALLING_INITIALIZED:
                    self._app_data_service.remove_agent_data(agent.name)
                    status = AgentStatus.CLEANING_CLEANED_ENTRY
            return AgentDTO(
                        status=AgentStatus.CLEANING_CLEANED,
                        break_status=agent.break_status,
                        clean_status=AgentStatus.CLEANING_CLEANED,
                        name=agent.name,
                        home=agent.home,
                        group=agent.group,
                        shell=agent.shell,
                        source_dir_path=agent.source_dir_path,
                        temp_path=agent.temp_path,
                        target_path=agent.target_path,
                        exceptions={
                            'installation': agent.exceptions['installation']
                        }
                    )
    def _return_without_cleaning(self, agent) -> AgentDTO:
         return AgentDTO(
                status=AgentStatus.CLEANING_CLEANED,
                break_status=agent.break_status,
                clean_status=AgentStatus.CLEANING_NO_NEEDED,
                name=agent.name,
                home=agent.home,
                group=agent.group,
                shell=agent.shell,
                source_dir_path=agent.source_dir_path,
                temp_path=agent.temp_path,
                target_path=agent.target_path,
                exceptions={
                    'installation': agent.exceptions['installation']
            }
        )


    def _check_is_cleaning_needed(self, agent: AgentDTO) -> bool:
        return agent.break_status != AgentStatus.INSTALLING_CHECKING_AGENT_EXISTS