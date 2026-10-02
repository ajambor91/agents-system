import os
from .class_loader import ClassLoader
from .class_builder import ClassBuilder

from lib.configuration import Configuration, ConfigurationWrapper
from manifests.app.manifests_app import ManifestsApp
from shared.json_loader import JsonLoader
from .models.data_class import DataClass
from .instance_manager import InstanceManager
from .instance_manager_wrapper import InstanceManagerWrapper
class RuntimeApp:
    config_path: str | None = None
    configuration: Configuration | None = None
    manifests: ManifestsApp | None = None
    instances: dict[str, object] | None = None
    instance_manager: InstanceManager | None = None
    def __init__(self):
        self.config_path = os.environ["ABSOLUTE_CONFIG_PATH"]
        self._build_class_tree()

    def _build_class_tree(self):
        config_file = JsonLoader.getJsonFileContent(self.config_path)
        variables = config_file.get("variables")
        if not isinstance(variables, list):
            raise ValueError("Configuration document must contain variables")
        self.manifests = ManifestsApp()
        self.configuration = Configuration(variables)
        modules_json_content = JsonLoader.getJsonFileContent(
            type(self.configuration).MODULES_MANIFEST_PATH
        )
        self.manifests.validate_manifest(modules_json_content)

        class_builder = ClassBuilder(ClassLoader(modules_json_content), self.configuration)
        self.instances = class_builder.build_class_tree()
        self.instance_manager = InstanceManager(self.instances)

        self.instance_manager.register('configuration_block', Configuration, self.configuration)
        self.instance_manager.register('instance-manager', InstanceManagerWrapper, InstanceManagerWrapper(self.instance_manager))
        self.instance_manager.register('manifests', ManifestsApp, self.manifests)
        self.instance_manager.register('configuration', ConfigurationWrapper, ConfigurationWrapper(self.configuration))

    def get_data(self):
        if self.configuration is None or self.instance_manager is None:
            raise RuntimeError("RuntimeApp is not properly initialized.")
        return DataClass(self.configuration, self.instance_manager)
        
        
            
