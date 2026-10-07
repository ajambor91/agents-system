from __future__ import annotations

from ..context import ApplicationContext

from collections.abc import Mapping
from typing import Any


class AgentsDeleteService:


    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        return {
            "status": "not-implemented",
            "agent": flags.get('name'),
            "message": "Delete agent is not implemented.",
        }
