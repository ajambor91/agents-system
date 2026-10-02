"""Display the selected execution mode in human console menus."""
from ..models import ApiResult
from .renderer import Renderer


class RuntimeStatusRenderer:
    @staticmethod
    def banner(mode: str, *, runtime_available: bool) -> str:
        if mode in {"json", "agent"}:
            return ""
        renderer = Renderer(mode)
        return renderer.runtime_status(runtime_available)

    @classmethod
    def prepend(cls, result: ApiResult, mode: str, *, runtime_available: bool) -> ApiResult:
        if result.exit_code == 0 and result.stdout:
            result.stdout = cls.banner(mode, runtime_available=runtime_available) + result.stdout
        return result
