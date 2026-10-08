
from dataclasses import dataclass


@dataclass(slots=True)
class ExclusiveGroup:
    members: list[str]
    minimum: int
    maximum: int