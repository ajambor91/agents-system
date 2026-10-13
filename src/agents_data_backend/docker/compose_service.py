
from .compose_state import ComposeState

from pathlib import Path

class ComposeService: 
    _compose_state: ComposeState

    def __init__(self, path: str):
        self._compose_state = ComposeState.createState(Path(path).absolute())

    @property
    def compose_state(self) -> ComposeState:
        return self._compose_state