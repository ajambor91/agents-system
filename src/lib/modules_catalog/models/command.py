
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from .flag import Flag

if TYPE_CHECKING:
    from .module import Module
from .command_input import CommandInput
from .exclusive_group import ExclusiveGroup

@dataclass(slots=True)
class Command:
    name: str
    method: str | None
    description: str
    usage: str
    implementation_status: str
    flags: list[Flag]

    input: CommandInput | None = None
    exclusive_groups: list[ExclusiveGroup] = field(default_factory=list)

    module: Module = field(
        init=False,
        repr=False,
    )
