"""Common lifecycle contract and manifest-driven help."""
from abc import ABC, abstractmethod
import argparse
from pathlib import Path
from typing import Any

from ..consts import HELP_MANIFEST_FILES
from ..enums import InstallerMode
from ..errors import InstallationError
from ..shared.help import read_help, render_help


class InstallerParent(ABC):
    operation: InstallerMode

    @abstractmethod
    def execute(self, arguments: argparse.Namespace) -> dict[str, Any]:
        """Execute one confirmed lifecycle operation."""

    def help(self) -> str:
        filename = HELP_MANIFEST_FILES[self.operation.value]
        path = Path(__file__).resolve().parents[1] / 'resources' / filename
        return render_help(read_help(path, self.operation.value))

    def require_yes(self, arguments: argparse.Namespace) -> None:
        if not getattr(arguments, 'yes', False):
            raise InstallationError('Wymagana flaga --yes; użyj --help, aby zobaczyć opcje')
