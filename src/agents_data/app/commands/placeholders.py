import argparse
from ..commands.base import CommandBase

class MemoryWriteCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        print("not implemented")
        return 0

class MemoryGetCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        print("not implemented")
        return 0

class MemoryFindCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        print("not implemented")
        return 0

class DriveSyncCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        print("not implemented")
        return 0

class SyncCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        print("not implemented")
        return 0