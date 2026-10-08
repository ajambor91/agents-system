
import logging
import argparse
from ..commands.base import CommandBase

LOGGER = logging.getLogger(__name__)


class MemoryWriteCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        LOGGER.info('Starting placeholders.execute')
        print("not implemented")
        return 0

class MemoryGetCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        LOGGER.info('Starting placeholders.execute')
        print("not implemented")
        return 0

class MemoryFindCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        LOGGER.info('Starting placeholders.execute')
        print("not implemented")
        return 0

class DriveSyncCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        LOGGER.info('Starting placeholders.execute')
        print("not implemented")
        return 0

class SyncCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        LOGGER.info('Starting placeholders.execute')
        print("not implemented")
        return 0