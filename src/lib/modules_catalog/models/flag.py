
from typing import Any

from dataclasses import dataclass


@dataclass(slots=True)
class Flag:
    name: str
    short: str | None
    long: str | None
    aliases: list[str]
    description: str
    usage: str
    takes_value: bool
    type: str
    required: bool
    default: Any | None = None
    value: Any | None = None