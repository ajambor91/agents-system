from enum import Enum

class AgentStatus(Enum):
    INITIALIZED = 'initialized'
    VALIDATED = 'validated'
    ASSIGNED = 'assigned'
    PREPARED = 'prepared'
    SYSTEM_INSTALLED = 'system_installed'