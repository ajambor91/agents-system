from dataclasses import dataclass, field
from .meta_data_class import MetaDataClass


@dataclass
class ModuleEntry:
    absolute_module_path: str
    is_runtime: bool
    meta_data: MetaDataClass

    runtime: list[str] = field(default_factory=list)
    module_name: str = ""