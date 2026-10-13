from __future__ import annotations

from lib.compose_loader import ComposeLoader, ComposeData
from pathlib import Path
from threading import Lock


class ComposeState:
    _instance: ComposeState | None = None
    _token = object()
    _lock = Lock()

    def __new__(
        cls,
        token: object,
        path: Path
    ) -> ComposeState:

        if token is not cls._token:
            raise RuntimeError(
                "Cannot create instance from the outside"
            )

        if cls._instance is not None:
            raise RuntimeError(
                "ComposeState is singleton"
            )

        instance = super().__new__(cls)
        return instance

    def __init__(
        self,
        token: object,
        path: Path
    ) -> None:
        self._compose_data = ComposeLoader.loadYaml(path)

    @property
    def compose_data(self) -> ComposeData:
        return self._compose_data

    @classmethod
    def createState(cls, path: Path) -> ComposeState:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(cls._token, path)

            return cls._instance