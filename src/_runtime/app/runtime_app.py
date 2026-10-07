
import logging

import os

from . import HealthCheck
from . import ClassLoader
from . import ClassBuilder
from typing import Any
from lib.configuration import Configuration, ConfigurationWrapper
from manifests.app.manifests_app import ManifestsApp
from lib.json_loader import JsonLoader
from .models import DataClass
from . import InstanceManager
from . import RuntimeApiWrapper
from lib.modules_catalog import ModulesFactory, ModulesCatalog
from .state_provider import StateProvider
LOGGER = logging.getLogger(__name__)


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
        modules_json_content = self.manifests.load_modules_manifest(
            type(self.configuration).MODULES_MANIFEST_PATH
        )
        LOGGER.info("Loaded runtime modules manifest: path=%s", type(self.configuration).MODULES_MANIFEST_PATH)
        class_builder = ClassBuilder(ClassLoader(modules_json_content), self.configuration)

        self.instances = class_builder.build_class_tree()
        self.instance_manager = InstanceManager(self.instances)
        self.instance_manager.initialize_main_application(
            self.configuration,
            self._bootstrap_runtime_api(
                instance_manager=self.instance_manager,
                json_content=modules_json_content
        ))
        self.instance_manager.register('configuration_block', Configuration, self.configuration)
        self.instance_manager.register('manifests', ManifestsApp, self.manifests)
        self.instance_manager.register('configuration', ConfigurationWrapper, ConfigurationWrapper(self.configuration))
        self.instance_manager.register('health-check', HealthCheck, HealthCheck())
        
    def get_data(self):
        if self.configuration is None or self.instance_manager is None:
            raise RuntimeError("RuntimeApp is not properly initialized.")
        return DataClass(self.configuration, self.instance_manager)
    
    def _bootstrap_runtime_api(self, instance_manager: InstanceManager, json_content: dict[str, Any]) -> RuntimeApiWrapper:
        return RuntimeApiWrapper(instance_manager, StateProvider(ModulesFactory.create_modules_from_dict(json_content)))
        
        
            
