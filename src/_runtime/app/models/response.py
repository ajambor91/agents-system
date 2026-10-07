"""Default response data for the JSON message protocol."""
from __future__ import annotations
from typing import Any

class Response:
    def __init__(self, request_id: str, successful: bool, result: Any = None, error: dict[str, Any] | None = None) -> None:
        self._request_id = request_id
        self._successful = successful
        print("RESPONSE RESULS")
        print(result)
        self._result = result
        self._error = dict(error) if error is not None else None

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def successful(self) -> bool:
        return self._successful

    @property
    def result(self) -> Any:
        return self._result

    @property
    def error(self) -> dict[str, Any] | None:
        return self._error
    
    def to_dict(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "successful": self.successful, "result": self.result, "error": self.error}
