from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ..enums import AgentStatus

@dataclass(frozen=True)
class MessageResultDTO:
    status: AgentStatus | None = None
    break_status: AgentStatus | None = None
    name: str | None = None
    message: str | None = None
    exceptions: dict[str, Exception] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            'break_status': self.break_status.value if self.break_status else None,
            "name": self.name,
            "message": self.message,
            "exceptions": {
                key: getattr(exc, "details", str(exc))
                for key, exc in self.exceptions.items()
            } if self.exceptions else None
        }