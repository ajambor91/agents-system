from __future__ import annotations

import json
import os
import pwd

from collections.abc import Mapping
from typing import Any

from ..context import ApplicationContext
from .agent_services_factory import AgentServicesFactory


class AgentsWakeupService:
    """Deliver the supplied envelope through the gateway wakeup service."""

    def __init__(self, services_factory: AgentServicesFactory) -> None:
        self._services_factory = services_factory

    MAX_ENVELOPE_BYTES = 1024 * 1024


    def execute(self, flags: Mapping[str, Any], context: ApplicationContext) -> dict[str, Any]:
        envelope = flags.get("envelope")
        if not isinstance(envelope, dict):
            raise ValueError("Message envelope must be a JSON object.")
        if len(json.dumps(envelope).encode("utf-8")) > self.MAX_ENVELOPE_BYTES:
            raise ValueError("Message envelope exceeds 1 MiB.")
        caller = os.environ.get("SUDO_USER") or pwd.getpwuid(os.geteuid()).pw_name
        services = self._services_factory.create(context, flags)
        result = services.wakeup.execute(
            agent_name=flags.get('name'),
            envelope=envelope,
            caller_user=caller,
            timeout=flags.get("timeout", 600),
        )
        return {
            "agent": flags.get('name'),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
