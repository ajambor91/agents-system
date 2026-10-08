from __future__ import annotations

import logging

from ..context import ApplicationContext

from collections.abc import Mapping
from typing import Any


LOGGER = logging.getLogger(__name__)


class AgentsDeleteService:


    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        LOGGER.info('Requesting agent deletion agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        return {
            "status": "not-implemented",
            "agent": flags.get('name'),
            "message": "Delete agent is not implemented.",
        }
