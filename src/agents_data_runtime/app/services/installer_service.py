from .system_service import SystemService
from .temp_files_service import TempFilesService
from .app_data_service import AppDataService
from ..agent import AgentOpenclaw, Agent
from ..ports import AgentRuntimeInstallAll
from ..enums import AgentStatus
from ..models import AgentDTO
from lib.configuration import Configuration
class InstallerService:
    _temp_service: TempFilesService
    _system_service: SystemService
    _agents_runtime:  AgentRuntimeInstallAll
    _app_data_service: AppDataService
    _configuration: Configuration

    def __init__(self, configuration: Configuration, temp_service: TempFilesService, system_service: SystemService, agent_runtime: AgentRuntimeInstallAll, app_data: AppDataService):
        self._temp_service = temp_service
        self._system_service = system_service
        self._agents_runtime = agent_runtime
        self._app_data_service = app_data
        self._configuration = configuration

    def install(self, path: str, force: bool) -> AgentDTO:
        status = AgentStatus.INSTALLING_UNINITIALIZED
        agent: Agent | None = None
        try:
            agent_config = self._app_data_service.get_agent_data(path)
            status = AgentStatus.INSTALLING_LOAD_AGENT_DATA
            agent = AgentOpenclaw.create(path, agent_config)
            agent.update_status(AgentStatus.INSTALLING_CHECKING_AGENT_EXISTS)
            if self._app_data_service.is_agent_exists(agent.get_agent_name()):
                raise Exception("Agent exists")
            agent_source_dir_path = self._app_data_service.create_source_path(agent.get_agent_source_dir())
            agent.update_status(AgentStatus.INSTALLING_CREATED_SOURCE_PATH)
            temp_path = self._temp_service.create_temp_dir(agent.get_agent_name())
            agent.update_status(AgentStatus.INSTALLING_CREATED_TEMP_DIR)
            target_path = self._app_data_service.create_target_path(agent.get_agent_name())
            agent.update_status(AgentStatus.INSTALLING_CREATED_TARGET_DIR)
            agent.update_agents_paths(agent_source_path=agent_source_dir_path, agent_temp_path=temp_path, agent_target_path=target_path)
            self._app_data_service.copy_agents_files(agent.get_agent_source_dir_path(), agent.get_agent_temp_path())
            agent.update_status(AgentStatus.INSTALLING_COPIED_TEMP)
            self._system_service.create_agent_user(
                agent.get_agent_name(),
                agent.get_agent_group(),
                agent.get_agent_home(),
                agent.get_agent_shell()
                )
            agent.update_status(AgentStatus.INSTALLING_USER_CREATED)
            self._system_service.set_dir_privs(agent.get_home_path(),agent.get_agent_name(), 'adam')
            agent.update_status(AgentStatus.INSTALLING_SET_PRIV)
            self._agents_runtime.add_agent(agent.get_agent_name(),agent.get_agent_home(), agent.get_agent_model(), force)
            agent.update_status(AgentStatus.INSTALLING_AGENBT_RUNTIME_INSTALLED)
            self._app_data_service.copy_agents_files(agent.get_agent_temp_path(), agent.get_agent_target_path())
            agent.update_status(AgentStatus.INSTALLING_COPIED_DATA_FILES)
            agent.set_lib_path()
            self._app_data_service.remove_data(agent.get_agent_temp_path())
            agent.update_status(AgentStatus.INSTALLING_REMOVED_TEMP)
            self._app_data_service.add_agent_data(agent.get_agent_name(), agent.get_agent_target_path())
            agent.update_status(AgentStatus.INSTALLING_ENTRY_ADDED)
            self._system_service.link_agent_files(f"{agent.get_lib_path()}/{type(self._configuration).AGENT_PERSONALITY_DIR_NAME}",agent.get_home_path(), "md")
            agent.update_status(AgentStatus.INSTALLING_LINKED_AGENT_PERSONALITY_FILES)
            self._agents_runtime.apply_identity(agent.get_agent_name(), agent.get_agent_home())
            agent.update_status(AgentStatus.INSTALLING_APPLIED_PERSONALITY)
            self._system_service.link_agent_files(f"{agent.get_lib_path()}/{type(self._configuration).AGENT_SCRIPTS_SOURCE_DIR_NAME}",f"{agent.get_home_path()}/{type(self._configuration).AGENT_SCRIPTS_SOURCE_DIR_NAME}", "js")
            agent.update_status(AgentStatus.INSTALLING_LINKED_AGENT_SCRIPTS_FILES)
            agent.update_status(AgentStatus.INSTALLING_INSTALLED)
            return AgentDTO(
                status=agent.get_status(),
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
            if isinstance(agent, Agent):
                status = agent.get_status() if agent.get_status() else status
                return AgentDTO(
                    status=AgentStatus.INSTALLING_INSTALLATION_ERROR,
                    break_status=status,
                    name=agent.get_agent_name(),
                    home=agent.get_home_path(),
                    group=agent.get_agent_group(),
                    shell=agent.get_agent_shell(),
                    source_dir_path=agent.get_agent_source_dir_path(),
                    temp_path=agent.get_agent_temp_path(),
                    target_path=agent.get_agent_target_path(),
                    exceptions={
                        'installation': e
                    }
                )
            return AgentDTO(
                status=AgentStatus.INSTALLING_INSTALLATION_ERROR,
                break_status=status,
                exceptions={
                    'installation': e
                }
                )


  




