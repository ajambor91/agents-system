"""Show the tool policy currently authored for one OpenClaw agent."""

from __future__ import annotations

import argparse
import json

from app.commands.base import Command
from app.services.agent_catalog import AgentCatalog
from app.services.openclaw import OpenClawService
from app.services.process import ProcessRunner


class ToolsCommand(Command):
    """Read the applied OpenClaw tool policy without mutating it."""

    def execute(self, args: argparse.Namespace) -> int:
        if not AgentCatalog.AGENT_PATTERN.fullmatch(args.name):
            raise ValueError(f"Invalid agent name: {args.name}")
        policy = self._openclaw().get_agent_tools(args.name)
        document = {"agent": args.name, "tools": policy}
        if args.json:
            print(json.dumps(document, indent=2, ensure_ascii=False))
            return 0

        print(f"agent:       {args.name}")
        if not policy:
            print("tools:       OpenClaw defaults (no authored policy)")
            return 0
        print(f"profile:     {policy.get('profile') or '-'}")
        self._print_names("allow", policy.get("allow"))
        self._print_names("also allow", policy.get("alsoAllow"))
        self._print_names("deny", policy.get("deny"))
        return 0

    @staticmethod
    def _print_names(label: str, value: object) -> None:
        names = value if isinstance(value, list) else []
        print(f"{label + ':':<12}{', '.join(str(item) for item in names) or '-'}")

    def _openclaw(self) -> OpenClawService:
        runner = ProcessRunner()
        return OpenClawService(
            binary=self.context.openclaw_bin,
            gateway_user=self.context.gateway_user,
            process_runner=runner,
        )
