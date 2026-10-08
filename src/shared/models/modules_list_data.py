"""Shared data returned by installed and resident module readers."""
from dataclasses import dataclass, field


@dataclass(slots=True)
class ModuleData:
    module_name: str
    reunning: bool = False
    description: str = ""


@dataclass(slots=True)
class ModulesListData:
    modules: dict[str, ModuleData] = field(default_factory=dict)
