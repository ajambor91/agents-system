from __future__ import annotations

import logging

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


LOGGER = logging.getLogger(__name__)


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
        LOGGER.info('Submitting message to communication backend')
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
            LOGGER.warning("Message submission rejected: http_status=%s", exc.code)
            detail = exc.read().decode("utf-8", errors="replace")
            raise AppCommError(
                f"app-comm odrzucił wiadomość (HTTP {exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            LOGGER.error("Message submission transport failed: reason=%s", type(exc.reason).__name__)
            raise AppCommError(
                f"Nie można połączyć się z app-comm pod {self.messages_url}: "
                f"{exc.reason}"
            ) from exc

        message_id = body.get("messageId")
        if not isinstance(message_id, str) or not message_id:
            LOGGER.error("Message submission response missing messageId")
            raise AppCommError("app-comm zwrócił odpowiedź bez messageId")
        LOGGER.info("Message accepted: message_id=%s status=%s", message_id, body.get("status", "accepted"))
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
