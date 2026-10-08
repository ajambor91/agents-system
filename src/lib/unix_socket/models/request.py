"""Default request data for the JSON message protocol."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

class Request:
    def __init__(self, operation: str, payload: Mapping[str, Any] | None = None, *, request_id: str | None = None, metadata: Mapping[str, str] | None = None) -> None:
        self._operation = operation
        self._payload = dict(payload or {})
        self._request_id = request_id or str(uuid4())
        self._metadata = dict(metadata or {})

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def payload(self) -> Mapping[str, Any]:
        return self._payload

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def metadata(self) -> Mapping[str, str]:
        return self._metadata

    def to_mapping(self) -> Mapping[str, Any]:
        return {"request_id": self.request_id, "operation": self.operation, "payload": self.payload, "metadata": self.metadata}
