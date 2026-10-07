from __future__ import annotations

from enum import Enum

class ManifestKind(str, Enum):
    AGENTS_SYSTEM_MODULES = "agents-system-modules-manifest"
    MODULE = "module-manifest"
    ENVIRONMENT = "agents-system-environment"
