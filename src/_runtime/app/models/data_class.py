from dataclasses import dataclass, field
from ..configuration import Configuration
from  manifests.app.manifests_app import ManifestsApp

@dataclass
class DataClass:
    configuration: type[Configuration]
    instances: dict[str, object]
    manifests: ManifestsApp
    
    




