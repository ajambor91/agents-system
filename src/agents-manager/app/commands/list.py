"""List persisted agents after synchronizing runtime and OpenClaw state."""

from __future__ import annotations

import argparse
import json

from app.commands.base import Command
from app.services.agent_registry import AgentRegistryService
from app.services.openclaw import OpenClawService
from app.services.process import ProcessRunner
from app.services.state import AgentStateService


class ListCommand(Command):
    """Synchronize agents.json and render a compact inventory."""

    def execute(self, args: argparse.Namespace) -> int:
        registry = self._registry().sync()
        if args.json:
            print(json.dumps(registry, indent=2, ensure_ascii=False))
            return 0

        agents = registry["agents"]
        if not agents:
            print("No agents registered.")
            return 0

        print("NAME\tSTATUS\tOPENCLAW\tTASKS\tWORKSPACE")
        for name, record in agents.items():
            tasks = record["tasks"]
            task_summary = (
                f"{tasks['status']} "
                f"({tasks['running']}/{tasks['total']})"
            )
            print(
                f"{name}\t{record['status']}\t"
                f"{record['openclaw']['status']}\t"
                f"{task_summary}\t"
                f"{record.get('workspace') or '-'}"
            )
        return 0

    def _registry(self) -> AgentRegistryService:
        runner = ProcessRunner()
        state = AgentStateService(self.context, runner)
        openclaw = OpenClawService(
            binary=self.context.openclaw_bin,
            gateway_user=self.context.gateway_user,
            process_runner=runner,
        )
        return AgentRegistryService(
            self.context,
            state,
            openclaw,
        )
