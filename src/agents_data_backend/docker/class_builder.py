from __future__ import annotations

from .interfaces import (
    ComposeApi,
    CandidatesApi,
    StackManagerApi,
    DockerUnitsApi,
)

from .stack_manager import StackManager
from .candidates_service import CandidatesService
from .compose_service import ComposeService
from .docker_units_service import DockerUnitsService


class ClassBuilder:

    _candidates: CandidatesApi | None = None
    _compose: ComposeApi | None = None
    _docker_states: StackManagerApi | None = None
    _docker_units: DockerUnitsApi | None = None

    @classmethod
    def build(cls) -> type[ClassBuilder]:

        if any((
            cls._candidates is not None,
            cls._compose is not None,
            cls._docker_states is not None,
            cls._docker_units is not None,
        )):
            raise RuntimeError("Classes already initialized")

        stack = StackManager()
        compose = ComposeService()
        candidates = CandidatesService()
        docker_units = DockerUnitsService()

        stack.initialize(
            compose_service=compose,
            candidates_service=candidates,
            docker_units_service=docker_units
        )

        compose.initialize(
            path=stack.docker_compose_file,
            candidates_service=candidates
        )

        docker_units.initialize(
            docker_client=stack.docker_client
        )

        candidates.initialize(
            docker_units=docker_units,
            compose_service=compose
        )

        cls._docker_states = stack
        cls._compose = compose
        cls._candidates = candidates
        cls._docker_units = docker_units

        return cls

    @classmethod
    def candidates_api(cls) -> CandidatesApi:
        if not isinstance(cls._candidates, CandidatesApi):
            raise RuntimeError("CandidatesService not initialized")
        return cls._candidates

    @classmethod
    def compose_api(cls) -> ComposeApi:
        if not isinstance(cls._compose, ComposeApi):
            raise RuntimeError("ComposeService not initialized")
        return cls._compose

    @classmethod
    def docker_states(cls) -> StackManagerApi:
        if not isinstance(cls._docker_states, StackManagerApi):
            raise RuntimeError("StackManager not initialized")
        return cls._docker_states

    @classmethod
    def docker_units_api(cls) -> DockerUnitsApi:
        if not isinstance(cls._docker_units, DockerUnitsApi):
            raise RuntimeError("DockerUnitsService not initialized")
        return cls._docker_units

    @classmethod
    def get_all(
        cls
    ) -> tuple[CandidatesApi, ComposeApi, StackManagerApi, DockerUnitsApi]:
        return (
            cls.candidates_api(),
            cls.compose_api(),
            cls.docker_states(),
            cls.docker_units_api()
        )