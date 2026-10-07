import logging
from dataclasses import dataclass

from lib.modules_catalog import Module, ModulesCatalog


LOGGER = logging.getLogger(__name__)


@dataclass
class State:
    modules: dict[str, Module]


@dataclass
class StateFactoryArg:
    modules_catalog: ModulesCatalog


class AppStateRemote:
    _instance: "AppStateRemote | None" = None
    _create_token = object()
    _is_runtime_mode: bool = False

    def __new__(cls, token: object, state: State):
        if token is not cls._create_token:
            raise RuntimeError(
                f"{cls.__name__} can only be created via init_state()"
            )

        return super().__new__(cls)

    def __init__(self, token: object, state: State):
        self._state = state

    @classmethod
    def init_state(
        cls,
        state: State,
        is_runtime_mode: bool,
    ) -> "AppStateRemote":
        cls._is_runtime_mode = is_runtime_mode

        if not cls._is_runtime_mode:
            LOGGER.error(
                "Cannot initialize AppStateRemote outside runtime mode"
            )
            raise RuntimeError(
                "Cannot initialize AppStateRemote outside runtime mode"
            )

        if cls._instance is None:
            cls._instance = cls(cls._create_token, state)

        return cls._instance

    @classmethod
    def get_state(cls) -> State | None:
        if not cls._is_runtime_mode:
            LOGGER.warning(
                "Cannot get AppStateRemote state outside runtime mode"
            )
            return None

        if cls._instance is None:
            LOGGER.warning(
                "AppStateRemote state wasn't initialized yet"
            )
            return None

        return cls._instance._state


class StateFactory:

    @staticmethod
    def create_state(args: StateFactoryArg) -> State:
        return State(
            modules=args.modules_catalog.modules
        )