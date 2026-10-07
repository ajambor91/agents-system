from __future__ import annotations
from typing import TYPE_CHECKING
import inspect
import threading
from .models import ManagedInstance
if TYPE_CHECKING:
    from agents_system import Application as AgentsSystem
from .runtime_api_wrapper import RuntimeApiWrapper
from lib.configuration import Configuration

class InstanceManager:
    """Hold references to class objects, not instances."""
    _instances: dict[str, ManagedInstance] = None
    _main_app: AgentsSystem | None = None
    def __init__(self, instances: dict[str, ManagedInstance] = None) -> None:
        self._instances = instances if instances is not None else {}
        self._lock = threading.RLock()

    def register(self, name: str, cls: type, instance: object) -> None:
        if not inspect.isclass(cls):
            raise TypeError(f"{name} is not a class")
        if not isinstance(instance, cls):
            raise TypeError(f"{name} is not an instance of {cls.__name__}")
        with self._lock:
            if name in self._instances:
                raise ValueError(f"Instance already registered: {name}")
            managed_class = ManagedInstance(instance_object=instance, instance_class=cls, class_name=name)     
            self._instances[name] = managed_class

    def get(self, name: str) -> ManagedInstance:
        with self._lock:
            return self._instances[name]
    
    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._instances)
    def list_managed_instances(self) -> list[ManagedInstance]:
        with self._lock:
            return list(self._instances.values())
        
    def initialize_main_application(self, configuration: Configuration, runtime_api: RuntimeApiWrapper):
        # self._main_app = self._instances[type(configuration).MAIN_APP_NAME].instance_object
        self._main_app = self._instances['agents_system'].instance_object

        if self._main_app is None:
            raise Exception("APP MAIN IS NONE")
        self._main_app.initialize(runtime_api)

    
         

    