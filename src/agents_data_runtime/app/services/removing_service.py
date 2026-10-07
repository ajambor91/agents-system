from .system_service import SystemService
from .loader_data_service import LoaderDataService
from .app_data_service import AppDataService
from ..agent import AgentOpenclaw
from ..ports import AgentRuntimeRemove
from ..ports.agent_runtime_install import AgentRuntimeInstall
class RemovingService:
    _loader_service: LoaderDataService
    _system_service: SystemService
    _agents_runtime: AgentRuntimeRemove
    _app_data_service: AppDataService

    def __init__(self, loader_service: LoaderDataService, system_service: SystemService, agent_runtime: AgentRuntimeInstall, app_data: AppDataService):
        self._loader_service = loader_service
        self._system_service = system_service
        self._agents_runtime = agent_runtime
        self._app_data_service = app_data

    def remove(self, name: str):
        agent_path = self._app_data_service.get_agents_path(name)
        agent_config = self._loader_service.get_agent_data(agent_path)
        agent = AgentOpenclaw.create(path, agent_config)
        self._system_service.remove_agent_user(agent.get_agent_name())
        self._agents_runtime.remove_agent(agent.get_agent_name())
        self._system_service.remove_data(agent.get_agent_target_path())
        self._system_service.remove_data(agent.get_agent_temp_path())
        self._app_data_service.remove_agent_data(agent.get_agent_name())

