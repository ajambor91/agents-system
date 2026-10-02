"""Show one synchronized agent record and its recent tasks."""

from __future__ import annotations

import argparse
import json

from .base import Command
from ..services.agent_catalog import AgentCatalog
from ..services.agent_registry import AgentRegistryService
from ..services.openclaw import OpenClawService
from ..services.process import ProcessRunner
from ..services.state import AgentStateService


class StatusCommand(Command):
    """Synchronize agents.json and render one selected agent."""

    def execute(self, args: argparse.Namespace) -> int:
        if not AgentCatalog.AGENT_PATTERN.fullmatch(args.name):
            raise ValueError(f"Invalid agent name: {args.name}")

        document = self._registry().sync()
        record = AgentRegistryService.get(
            document,
            args.name,
        )
        if args.json:
            print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0

        tasks = record["tasks"]
        openclaw = record["openclaw"]
        print(f"agent:       {record['id']}")
        print(f"name:        {record['name']}")
        print(f"status:      {record['status']}")
        print(f"managed:     {'yes' if record['managed'] else 'no'}")
        print(f"linux user:  {record.get('linux_user') or '-'}")
        print(f"workspace:   {record.get('workspace') or '-'}")
        print(f"runtime:     {record['runtime']['status']}")
        print(f"openclaw:    {openclaw['status']}")
        print(
            "tasks:       "
            f"{tasks['status']} "
            f"(total={tasks['total']}, "
            f"running={tasks['running']}, "
            f"failed={tasks['failed']})"
        )
        if tasks["active"]:
            print("active tasks:")
            for task in tasks["active"]:
                print(
                    f"  - {task.get('started_at') or '-'} "
                    f"{task.get('command') or '-'}"
                )
        if tasks["recent"]:
            print("recent tasks:")
            for task in tasks["recent"][:5]:
                print(
                    f"  - {task['status']} "
                    f"rc={task.get('return_code', '-')} "
                    f"{task.get('command') or '-'}"
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
