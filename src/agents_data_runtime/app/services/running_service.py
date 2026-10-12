
from ..ports.agent_runtime_run import AgentRuntimeRun
from .app_data_service import AppDataService
from ..agent import (AgentOpenclaw, Agent)
from ..enums import AgentStatus
from ..models import (MessageDTO, MessageResultDTO)
class RunningService:
    _agents_runtime: AgentRuntimeRun
    _app_data: AppDataService

    def __init__(self, agents_runtime: AgentRuntimeRun, app_data: AppDataService):
        self._agents_runtime = agents_runtime
        self._app_data = app_data


    def run_agent(self, message: MessageDTO) -> MessageResultDTO:
        agent: Agent | None = None
        status = message.status
        try:
            agent_path = self._app_data.get_agents_path(message.name)
            status = AgentStatus.REMOVING_GET_AGENT_PATH
            agent_config = self._app_data.get_agent_data(agent_path)
            status = AgentStatus.RUNNING_GET_AGENT_DATA
            agent = AgentOpenclaw.create(agent_path, agent_config)
            agent.update_status(AgentStatus.RUNNING_AGENT_CREATED)
            result = self._agents_runtime.run_agent(
                agent.get_agent_name(),
                message.message
                )
            return MessageResultDTO(
                status=AgentStatus.RUNNING_SUCCESS,
                name=agent.get_agent_name(),
                message=result
            )
        except Exception as e:
            name = message.name
            if isinstance(agent, Agent):
                status = agent.get_status() if agent.get_status() else status    
                name = agent.get_agent_name() if agent.get_agent_name() else name
            return MessageResultDTO(
                status=AgentStatus.RUNNING_FAILED,
                break_status=status,
                name=name,
                exceptions={
                    'running': e
                }
            )


    