
from __future__ import annotations

from dataclasses import dataclass

from .command import Command


@dataclass(slots=True)
class Module:
    module_name: str
    absolute_module_path: str
    section_name: str | None
    menu_name: str | None
    description: str
    commands: dict[str, Command]
    usage: str = ""
