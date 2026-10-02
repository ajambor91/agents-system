from __future__ import annotations

import json
import os
import pwd
import sys

from argparse import Namespace

from ..context import ApplicationContext
from ..services.process import ProcessRunner
from ..services.wakeup import WakeupService


class WakeupCommand:
    """Compatibility CLI around the gateway-owned WakeupService."""

    MAX_ENVELOPE_BYTES = 1024 * 1024

    def __init__(self, context: ApplicationContext) -> None:
        self.context = context

    def execute(self, args: Namespace) -> int:
        payload = sys.stdin.buffer.read(self.MAX_ENVELOPE_BYTES + 1)
        if len(payload) > self.MAX_ENVELOPE_BYTES:
            raise ValueError("Message envelope exceeds 1 MiB.")
        try:
            envelope = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Message envelope is not valid UTF-8 JSON.") from exc
        if not isinstance(envelope, dict):
            raise ValueError("Message envelope must be a JSON object.")
        caller = os.environ.get("SUDO_USER") or pwd.getpwuid(os.geteuid()).pw_name
        result = WakeupService(
            self.context, ProcessRunner(verbose=args.verbose)
        ).execute(
            agent_name=args.name,
            envelope=envelope,
            caller_user=caller,
            timeout=args.timeout,
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr and args.verbose:
            print(result.stderr.rstrip(), file=sys.stderr)
        return 0
