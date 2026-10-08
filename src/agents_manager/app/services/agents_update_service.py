from __future__ import annotations

import logging

from ..context import ApplicationContext

from collections.abc import Mapping
from typing import Any

from .agents_installator_service import AgentsInstallatorService


LOGGER = logging.getLogger(__name__)


class AgentsUpdateService:

    def __init__(self, installer: AgentsInstallatorService) -> None:
        self._installer = installer


    def execute(
        self,
        flags: Mapping[str, Any],
        context: ApplicationContext,
    ) -> dict[str, Any]:
        LOGGER.info('Updating agent agent=%s dry_run=%s', (flags or {}).get('name'), (flags or {}).get('dry_run', False))
        refresh = dict(flags)
        refresh.update(user=None, model=None, gateway_user=context.gateway_user,
                       force=True, operation="update")
        return self._installer.execute(refresh, context)
