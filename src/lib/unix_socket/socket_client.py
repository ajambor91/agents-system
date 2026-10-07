"""Small application-facing facade for Unix socket communication."""

from __future__ import annotations

import logging


from collections.abc import Mapping
from typing import Any


from .abstract import (
    AbstractMessageCodec,
    AbstractUnixSocketClient,
    AbstractUnixSocketTransport,
)
from .models import Request, Response, CheckStatus


LOGGER = logging.getLogger(__name__)


class SocketClient:
    """Connect, send a module method call and close the connection."""

    def __init__(
        self,
        client: AbstractUnixSocketClient,
        codec: AbstractMessageCodec,
        transport: AbstractUnixSocketTransport,
    ) -> None:
        # Keep the constructor compatible with SocketClientBuilder.
        self._client = client

    @property
    def is_connected(self) -> bool:
        """Return the underlying client's connection state."""
        return self._client.is_connected

    def socket_exists(self) -> bool:
        """Return whether the configured socket exists, independently of health."""
        return self._client.socket_exists()

    def connect(self) -> SocketClient:
        """Open the connection and return this facade."""
        self._client.connect()
        return self

    def close(self) -> SocketClient:
        """Close the connection and return this facade."""
        self._client.close()
        return self

    def send(
        self,
        module_name: str,
        method: str,
        kwargs: Mapping[str, Any] | None = None,
    ) -> Response:
        """Send module_name, method and kwargs in the existing request payload."""
        request = Request(
            operation=f"{module_name}.{method}",
            payload={
                "module_name": module_name,
                "method": method,
                "kwargs": dict(kwargs) if kwargs is not None else {},
            },
        )
        LOGGER.debug("Sending module request: module=%s method=%s request_id=%s", module_name, method, request.request_id)
        return self._client.request(request)
    def is_healthy(self) -> bool:
        """Check if the socket client is healthy."""
        LOGGER.debug("Checking runtime health")
        return self.send("health-check", "is_healthy").result

    def check_status(self) -> CheckStatus:
        """Check the status of the socket client."""

        return CheckStatus(self.send("health-check", "check_status").result)

    
        
        
