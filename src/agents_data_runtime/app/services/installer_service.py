from .system_service import SystemService
from .loader_data_service import LoaderDataService
from .app_data_service import AppDataService
from ..agent import AgentOpenclaw, Agent
from ..ports import AgentRuntimeInstall
from ..enums import AgentStatus
from ..models import AgentDTO
class InstallerService:
    _loader_service: LoaderDataService
    _system_service: SystemService
    _agents_runtime: AgentRuntimeInstall 
    _app_data_service: AppDataService

    def __init__(self, loader_service: LoaderDataService, system_service: SystemService, agent_runtime: AgentRuntimeInstall, app_data: AppDataService):
        self._loader_service = loader_service
        self._system_service = system_service
        self._agents_runtime = agent_runtime
        self._app_data_service = app_data

    def install(self, path: str, force: bool) -> AgentDTO:
        status = AgentStatus.INSTALLING_UNINITIALIZED
        agent: Agent | None = None
        try:
            agent_config = self._loader_service.get_agent_data(path)
            status = AgentStatus.INSTALLING_LOAD_AGENT_DATA
            agent = AgentOpenclaw.create(path, agent_config)
            agent_source_dir_path = self._system_service.create_source_path(agent.get_agent_source_dir())
            agent.update_status(AgentStatus.INSTALLING_CREATED_SOURCE_PATH)
            temp_path = self._system_service.create_temp_dir(agent.get_agent_name())
            agent.update_status(AgentStatus.INSTALLING_CREATED_TEMP_DIR)
            target_path = self._system_service.create_target_path(agent.get_agent_name())
            agent.update_status(AgentStatus.INSTALLING_CREATED_TARGET_DIR)
            agent.update_agents_paths(agent_source_path=agent_source_dir_path, agent_temp_path=temp_path, agent_target_path=target_path)
            self._system_service.copy_temp_files(agent.get_agent_temp_path(), agent.get_agent_source_dir_path())
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
            self._system_service.copy_agents_files(agent.get_agent_temp_path(), agent.get_agent_target_path())
            agent.update_status(AgentStatus.INSTALLING_COPIED_DATA_FILES)
            self._system_service.remove_data(agent.get_agent_temp_path())
            agent.update_status(AgentStatus.INSTALLING_REMOVED_TEMP)
            self._app_data_service.add_agent_data(agent.get_agent_name(), agent.get_agent_target_path())
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


  




