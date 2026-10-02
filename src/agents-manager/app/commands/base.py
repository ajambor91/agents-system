from __future__ import annotations

import argparse

from abc import ABC, abstractmethod

from ..context import ApplicationContext


class Command(ABC):

    def __init__(
        self,
        context: ApplicationContext,
    ) -> None:
        self.context = context

    @abstractmethod
    def execute(
        self,
        args: argparse.Namespace,
    ) -> int:
        raise NotImplementedError