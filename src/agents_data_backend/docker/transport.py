from __future__ import annotations
from lib.configuration import Configuration
from typing import ClassVar
from .module_creater import ModuleCreator
class Transport:
    _configuration: ClassVar[Configuration]
    _instance: Transport | None = None

    def __new__(cls):
        if cls._instance is None:
            raise Exception("Transport class can be created only once")
        
    def __init__(self, configuration: Configuration):
        type(self)._configuration = configuration

    @classmethod
    def get_configuration(cls) -> Configuration:
        return cls._configuration