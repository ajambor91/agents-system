from dataclasses import dataclass, field
from lib.configuration import Configuration
from ..instance_manager import InstanceManager
@dataclass
class DataClass:
    configuration: Configuration
    instance_manager: InstanceManager
    
    




