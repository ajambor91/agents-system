from lib.configuration import Configuration
from .services import (
    AgentsService,
    LoaderDataService,
    InstallerService,
    SystemService,
    AppDataService,
    RemovingService
)

from .adapters import OpenClawRuntime


class Application:
    _configuration: Configuration
    _agents_service: AgentsService
    def __init__(self, configuration: Configuration):
        self._configuration = configuration
        app_data_service: AppDataService = AppDataService(configuration)
        agent_runtime = OpenClawRuntime(configuration) 
        system_service = SystemService(configuration)
        loader_service = LoaderDataService(configuration)
        loader_service  = LoaderDataService(configuration)
        installer = InstallerService(
            system_service=system_service,
            loader_service=loader_service,
            app_data=app_data_service,
            agent_runtime=agent_runtime
        )
        removing_service: RemovingService = RemovingService(
            system_service=system_service,
            loader_service=loader_service,
            app_data=app_data_service,
            agent_runtime=agent_runtime
        )

        self._agents_service = AgentsService(
            installer_service=installer,
            removing_service=removing_service
            )

    def install_agent(self, path: str, force: bool = False):
        return self._agents_service.install_agent(path, force)

    def remove_agent(self, agent_name: str):
        return self._agents_service.removing_agent(agent_name)
