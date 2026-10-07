
from dataclasses import dataclass, field

from .module import Module
from .command import Command
@dataclass(slots=True)
class ModulesCatalog:
    schema_version: int
    version: int
    kind: str

    app_name: str
    absolute_path: str

    modules: dict[str, Module]
    modules_by_section: dict[str, Module]
    commands: dict[str, Command] = field(
        default_factory=dict,
        repr=False,
    )


