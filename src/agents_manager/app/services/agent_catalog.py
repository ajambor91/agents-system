from __future__ import annotations

import re

from pathlib import Path


class AgentCatalog:

    AGENT_PATTERN = re.compile(
        r"^[a-z0-9][a-z0-9_-]*$"
    )

    def __init__(
        self,
        agents_root: Path,
    ) -> None:

        self.agents_root = agents_root

    def list_agents(self) -> list[str]:

        if not self.agents_root.is_dir():
            return []

        agents: list[str] = []

        for path in self.agents_root.iterdir():

            if not path.is_dir():
                continue

            if path.name.startswith("."):
                continue

            if not self.AGENT_PATTERN.fullmatch(
                path.name
            ):
                continue

            if not (
                (path / "personality").is_dir()
                or
                (path / "resources").is_dir()
                or
                (path / "scripts").is_dir()
            ):
                continue

            agents.append(
                path.name
            )

        return sorted(agents)

    def get_agent_root(
        self,
        name: str,
    ) -> Path:

        if not self.AGENT_PATTERN.fullmatch(name):
            raise ValueError(
                f"Invalid agent name: {name}"
            )

        path = (
            self.agents_root
            / name
        )

        if not path.is_dir():
            raise FileNotFoundError(
                f"Agent does not exist: {name}"
            )

        return path