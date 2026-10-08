from lib.configuration import Configuration
from . import Renderer
from . import RuntimeStatusRenderer
from ..models import ApiResult
from .help_renderer import HelpRenderer
class RenderersFactory:
    _configuration: Configuration | None = None
    _settings: type[Configuration] | None = None
    _runtime_available = None

    def __init__(self,configuration: Configuration, runtime_available):
        self._configuration = configuration
        self._settings = type(self._configuration)
        self._runtime_available = runtime_available

    def create_renderer(self,mode: str) -> Renderer:
        if self._configuration is None or self._settings is None:
            raise Exception("Renderer's configuration or mode cannot be null")
        return Renderer(self._configuration, mode)

    def create_status_renderer(self, mode:str, renderer: Renderer) -> RuntimeStatusRenderer:
        if self._configuration is None or self._settings is None:
            raise Exception("Renderer's configuration or mode cannot be null")
        return RuntimeStatusRenderer(renderer, mode, self._runtime_available)

    def create_help_renderer(self, mode: str, renderer: Renderer) -> HelpRenderer:
        if self._configuration is None or self._settings is None:
            raise Exception("Renderer's configuration or mode cannot be null")
        return HelpRenderer(renderer, mode)
