
from dataclasses import dataclass


@dataclass(slots=True)
class CommandInput:
    source: str
    type: str
    maximum_bytes: int
