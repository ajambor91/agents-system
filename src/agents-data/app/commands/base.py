from __future__ import annotations
import argparse
from pathlib import Path
from abc import ABC, abstractmethod

class CommandBase(ABC):
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        pass

    def get_system_home(self, args: argparse.Namespace) -> Path:
        return Path(args.configuration.select("USER_SYSTEM_HOME"))
