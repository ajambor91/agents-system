from dataclasses import dataclass
from ..enums import AgentStatus

@dataclass(frozen=True)
class MessageDTO:
    status: AgentStatus | None = None
    name: str | None = None
    message: str | None = None