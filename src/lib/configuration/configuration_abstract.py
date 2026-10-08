from abc import ABC, ABCMeta, abstractmethod
from threading import RLock
from types import MappingProxyType
from typing import Any, ClassVar, Mapping


class ConfigurationMeta(ABCMeta):
    _lock = RLock()

    def __call__(cls, *args, **kwargs):
        with ConfigurationMeta._lock:
            if cls.__dict__.get("_instance") is not None:
                raise RuntimeError(
                    f"{cls.__name__} can be initialized only once"
                )

            instance = super().__call__(*args, **kwargs)

            type.__setattr__(cls, "_instance", instance)

            return instance

    def __getattr__(cls, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        if name not in cls.schema():
            raise AttributeError(name)

        if cls._instance is None:
            raise RuntimeError("Configuration is not initialized")

        return cls._values[name]

    def __setattr__(cls, name: str, value) -> None:
        if name in {"_instance", "_values"}:
            raise AttributeError(f"{name} is read-only")

        if not name.startswith("_") and name in cls.schema():
            raise AttributeError(
                f"Configuration field '{name}' is read-only"
            )

        super().__setattr__(name, value)

    def __delattr__(cls, name: str) -> None:
        if name in {"_instance", "_values"} or (
            not name.startswith("_") and name in cls.schema()
        ):
            raise AttributeError(f"Cannot delete: {name}")

        super().__delattr__(name)


class ConfigurationAbstract(
    ABC,
    metaclass=ConfigurationMeta
):
    __slots__ = ()

    _instance: ClassVar[object | None] = None
    _values: ClassVar[Mapping[str, Any]] = MappingProxyType({})

    def __init__(
        self,
        config: dict[str, Any] | list[dict[str, Any]]
    ) -> None:
        self._load(config)

    def __setattr__(self, name: str, value) -> None:
        raise AttributeError("Configuration is read-only")

    @classmethod
    @abstractmethod
    def schema(cls) -> Mapping[str, type]:
        pass

    @classmethod
    def _load(
        cls,
        config: dict[str, Any] | list[dict[str, Any]]
    ) -> None:

        # Convert the original JSON structure into a dictionary.
        if isinstance(config, list):
            values = {}

            for item in config:
                name = item["name"]

                if name in values:
                    raise ValueError(
                        f"Duplicate configuration field: {name}"
                    )

                values[name] = item["value"]

        elif isinstance(config, dict):
            values = config.copy()

        else:
            raise TypeError(
                "Configuration must be a dict or a list"
            )

        schema = cls.schema()

        missing = schema.keys() - values.keys()
        extra = values.keys() - schema.keys()

        if missing or extra:
            raise ValueError(
                f"Missing: {sorted(missing)}, "
                f"Unknown: {sorted(extra)}"
            )

        for name, expected_type in schema.items():
            value = values[name]

            if type(value) is not expected_type:
                raise TypeError(
                    f"{name}: expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

        # Replace all configuration values at once.
        type.__setattr__(
            cls,
            "_values",
            MappingProxyType(values)
        )

    @classmethod
    def refresh(
        cls,
        config: dict[str, Any] | list[dict[str, Any]]
    ) -> None:

        with ConfigurationMeta._lock:
            if cls._instance is None:
                raise RuntimeError(
                    "Configuration is not initialized"
                )

            cls._load(config)