from dataclasses import dataclass, field
from . import MetaDataClass
from typing import Any

@dataclass
class ModuleEntry:
    absolute_module_path: str
    is_runtime: bool
    meta_data: MetaDataClass
    manifests: dict[str, Any]
    runtime: list[str] = field(default_factory=list)
    module_name: str = ""