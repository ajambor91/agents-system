from lib.configuration import Configuration
from .services import (
    AgentsService,
    TempFilesService,
    InstallerService,
    SystemService,
    AppDataService,
    RemovingService,
    RunningService
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
        temp_service = TempFilesService(configuration)
        running_service = RunningService(
            agents_runtime=agent_runtime,
            app_data=app_data_service
            )
        installer = InstallerService(
            system_service=system_service,
            temp_service=temp_service,
            app_data=app_data_service,
            agent_runtime=agent_runtime,
            configuration=configuration
        )
        removing_service: RemovingService = RemovingService(
            system_service=system_service,
            temp_service=temp_service,
            app_data=app_data_service,
            agent_runtime=agent_runtime
        )

        self._agents_service = AgentsService(
            installer_service=installer,
            removing_service=removing_service,
            running_service=running_service
            )

    def install_agent(self, path: str, agent_name: str = None, user: str = None, model: str = None, dry_run: bool = False, force: bool = False):
        return self._agents_service.install_agent(path, force)

    def remove_agent(self, agent_name: str, dry_run: bool = False, force: bool = False):
        return self._agents_service.removing_agent(agent_name)

    def run_agent(self, agent_name: str, message: str):
        return self._agents_service.run_agent(agent_name, message)
