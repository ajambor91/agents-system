"""Display the selected execution mode in human console menus."""
from ..models import ApiResult
from . import Renderer


class RuntimeStatusRenderer:
    _renderer: Renderer | None = None
    _runtime_available = None
    _mode: str | None = None
    def __init__(self, renderer: Renderer, mode: str, runtime_available):
        self._renderer = renderer
        self._mode = mode
        self._runtime_available = runtime_available

    def banner(self) -> str:
        if self._mode in {"json", "agent"}:
            return ""
        return self._renderer.runtime_status(self._runtime_available)


    def prepend(self, result: ApiResult) -> ApiResult:
        if result.exit_code == 0 and result.stdout:
            result.stdout = self.banner() + result.stdout
        return result
