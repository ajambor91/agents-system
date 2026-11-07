from interfaces import (
    CandidatesApi,
    ComposeApi,
    DockerUnitsApi,
    StackManagerApi
)

from class_builder import ClassBuilder
from lib.configuration import Configuration

from .transport import Transport


class ModuleCreator:

    _configuration: Configuration
    _candidates: CandidatesApi
    _compose: ComposeApi
    _stack_manager: StackManagerApi
    _docker_units_service: DockerUnitsApi

    def __init__(self):
        self._configuration = Transport.get_configuration()

        builder = ClassBuilder.build()

        self._candidates = builder.candidates_api()
        self._compose = builder.compose_api()
        self._stack_manager = builder.docker_states()
        self._docker_units_service = builder.docker_units_api()

    # ============================
    # CONFIGURATION
    # ============================

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    # ============================
    # CANDIDATES
    # ============================

    @property
    def candidates(self) -> CandidatesApi:
        return self._candidates

    # ============================
    # COMPOSE
    # ============================

    @property
    def compose(self) -> ComposeApi:
        return self._compose

    # ============================
    # STACK MANAGER
    # ============================

    @property
    def stack_manager(self) -> StackManagerApi:
        return self._stack_manager

    # ============================
    # DOCKER UNITS
    # ============================

    @property
    def docker_units_service(self) -> DockerUnitsApi:
        return self._docker_units_service