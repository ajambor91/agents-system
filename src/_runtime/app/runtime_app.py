import os
from .class_loader import ClassLoader
from .class_builder import ClassBuilder

from .configuration import Configuration
from manifests.app.manifests_app import ManifestsApp
from shared.json_loader import JsonLoader
from .models.data_class import DataClass
class RuntimeApp:
    config_path = None
    configuration = None
    manifests = None
    instances = None

    def __init__(self):
        self.config_path = os.environ["ABSOLUTE_CONFIG_PATH"]
        self._build_class_tree

    def _build_class_tree(self):
        config_file = self.json_loader.setJsonFile(self.config_path).getJsonFile()
        if config_file is None:
            raise 
        self.manifests = ManifestsApp()
        self.configuration = Configuration()
        modules_json_content = JsonLoader.getJsonFileContent(self.configuration.MODULES_MANIFEST_PATH)
        self.manifests.validate_manifest(modules_json_content)

        class_builder = ClassBuilder(ClassLoader(modules_json_content))
        self.instances = class_builder.get_instancer()

    def get_data(self):
        return DataClass(self.configuration,  self.manifests, self.instances)
        
        
            
