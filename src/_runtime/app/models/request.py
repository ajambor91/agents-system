"""Default request data for the JSON message protocol."""

from __future__ import annotations

from typing import Any


class Request:
    def __init__(self, body: dict[str, Any]) -> None:
        self._validate(body)

        self._operation = body["operation"]
        self._payload = body["payload"]
        self._request_id = body["request_id"]
        self._metadata = body.get("metadata", {})

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def _validate(self, body: dict[str, Any]) -> None:
        if not isinstance(body, dict):
            raise TypeError("Request body must be a dict")

        if not body.get("operation"):
            raise ValueError("Request field 'operation' cannot be empty")

        if not body.get("request_id"):
            raise ValueError("Request field 'request_id' cannot be empty")

        payload = body.get("payload")

        if not isinstance(payload, dict) or not payload:
            raise ValueError("Request field 'payload' cannot be empty")

        if not payload.get("module_name"):
            raise ValueError(
                "Request payload field 'module_name' cannot be empty"
            )

        if not payload.get("method"):
            raise ValueError(
                "Request payload field 'method' cannot be empty"
            )