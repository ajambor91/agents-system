from .system_service import SystemService
from .loader_data_service import LoaderDataService
from .app_data_service import AppDataService
from ..agent import AgentOpenclaw
from ..ports import AgentRuntimeInstall
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

    def install(self, path: str, force: bool = False):
        agent_config = self._loader_service.get_agent_data(path)
        agent = AgentOpenclaw.create(path, agent_config)
        agent_source_dir_path = self._system_service.create_source_path(agent.get_agent_source_dir())
        temp_path = self._system_service.create_temp_dir(agent.get_agent_name())
        target_path = self._system_service.create_target_path(agent.get_agent_name())
        agent.update_agents_paths(agent_source_dir_path, temp_path, target_path)
        self._system_service.copy_temp_files(agent.get_agent_temp_path(), agent.get_agent_source_dir_path())
        self._agents_runtime.add_agent(agent.get_agent_name(),agent.get_agent_home(), agent.get_agent_model(), force)
        self._system_service.copy_agents_files(agent.get_agent_temp_path(), agent.get_agent_target_path())
        self._system_service.remove_data(agent.get_agent_temp_path())
        self._app_data_service.add_agent_data(agent.get_agent_name(), agent.get_agent_target_path())


