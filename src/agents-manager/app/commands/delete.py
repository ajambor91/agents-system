from __future__ import annotations

import argparse

from app.commands.base import Command


class DeleteCommand(Command):

    def execute(
        self,
        args: argparse.Namespace,
    ) -> int:

        print(
            f"[TODO] Delete agent: {args.name}"
        )

        return 0