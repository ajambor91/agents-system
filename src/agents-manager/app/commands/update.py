from __future__ import annotations

import argparse

from .base import Command
from .install import InstallCommand


class UpdateCommand(Command):

    def execute(
        self,
        args: argparse.Namespace,
    ) -> int:
        refresh = argparse.Namespace(
            name=args.name,
            user=None,
            model=None,
            gateway_user=self.context.gateway_user,
            force=True,
            dry_run=args.dry_run,
            verbose=args.verbose,
            operation="update",
        )
        return InstallCommand(self.context).execute(refresh)
