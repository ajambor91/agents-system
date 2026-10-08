from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ..enums import AgentStatus

@dataclass(frozen=True)
class AgentDTO:
    status: AgentStatus | None = None
    break_status: AgentStatus | None = None
    clean_status: AgentStatus | None = None
    name: str | None = None
    home: Path | None = None
    group: str | None = None
    shell: str | None = None
    source_dir_path: Path | None = None
    temp_path: Path | None = None
    target_path: Path | None = None
    exceptions: dict[str, Exception] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            'break_status': self.break_status.value if self.break_status else None,
            'clean_status': self.clean_status.value if self.clean_status else None,
            "name": self.name,
            "home": str(self.home) if self.home else None,
            "group": self.group,
            "shell": self.shell,
            "source": str(self.source_dir_path) if self.source_dir_path else None,
            "target": str(self.target_path) if self.target_path else None,
            "temp": str(self.temp_path) if self.temp_path else None,
            "exceptions": {
                key: getattr(exc, "details", str(exc))
                for key, exc in self.exceptions.items()
            } if self.exceptions else None
        }