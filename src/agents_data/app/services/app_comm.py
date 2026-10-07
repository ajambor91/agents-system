from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class AppCommError(RuntimeError):
    """A user-facing error returned by app-comm or its transport."""


@dataclass(frozen=True)
class SendResult:
    message_id: str
    status: str


class AppCommService:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        normalized = base_url.rstrip("/")
        self.messages_url = (
            normalized
            if normalized.endswith("/api/messages")
            else f"{normalized}/api/messages"
        )
        self.timeout = timeout

    def send_message(self, payload: dict[str, Any]) -> SendResult:
        request = urllib.request.Request(
            self.messages_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = self._json_response(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AppCommError(
                f"app-comm odrzucił wiadomość (HTTP {exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AppCommError(
                f"Nie można połączyć się z app-comm pod {self.messages_url}: "
                f"{exc.reason}"
            ) from exc

        message_id = body.get("messageId")
        if not isinstance(message_id, str) or not message_id:
            raise AppCommError("app-comm zwrócił odpowiedź bez messageId")
        return SendResult(
            message_id=message_id,
            status=str(body.get("status", "accepted")),
        )

    @staticmethod
    def _json_response(raw: bytes) -> dict[str, Any]:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppCommError("app-comm zwrócił niepoprawny JSON") from exc
        if not isinstance(value, dict):
            raise AppCommError("app-comm zwrócił niepoprawny format odpowiedzi")
        return value
