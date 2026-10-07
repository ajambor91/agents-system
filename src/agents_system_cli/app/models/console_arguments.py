"""Parsed console options and unchanged module argument tokens."""
from dataclasses import dataclass, field


@dataclass(slots=True)
class ConsoleArguments:
    mode: str = "human"
    help_requested: bool = False
    remaining: list[str] = field(default_factory=list)
