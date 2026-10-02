import logging
import json
import socketserver
from .exceptions.runtime_protocol_error import RuntimeProtocolError


LOGGER = logging.getLogger(__name__)

class RuntimeRequestHandler(socketserver.StreamRequestHandler):
    """One newline-delimited JSON request per connection."""
    MAX_MESSAGE_BYTES: int = 1024 * 1024
    def handle(self) -> None:
        self._initialize()
        self.connection.settimeout(15)

        try:

            raw = self.rfile.readline(
                self.MAX_MESSAGE_BYTES + 1
            )

            if len(raw) > self.MAX_MESSAGE_BYTES:
                raise RuntimeProtocolError(
                    "REQUEST_TOO_LARGE",
                    "Request exceeds 1 MiB",
                )

            if not raw or not raw.endswith(b"\n"):
                raise RuntimeProtocolError(
                    "INVALID_REQUEST",
                    "Expected newline-terminated JSON",
                )

            try:
                request = json.loads(raw)

            except (ValueError, UnicodeError) as exc:
                raise RuntimeProtocolError(
                    "INVALID_JSON",
                    "Invalid JSON request",
                ) from exc

            if not isinstance(request, dict):
                raise RuntimeProtocolError(
                    "INVALID_REQUEST",
                    "JSON request must be an object",
                )

            response = {
                "ok": True,
                "result": self.server.runtime.dispatch(
                    request
                ),
            }

        except RuntimeProtocolError as exc:

            response = {
                "ok": False,
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                },
            }

            if exc.details is not None:
                response["error"]["details"] = exc.details

        except (TimeoutError, OSError) as exc:

            response = {
                "ok": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": str(exc),
                },
            }

        except Exception:

            LOGGER.exception(
                "Unhandled runtime request failure"
            )

            response = {
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal runtime error",
                },
            }

        try:

            serialized = json.dumps(
                response,
                ensure_ascii=False,
                allow_nan=False,
            )

            self.wfile.write(
                (serialized + "\n").encode("utf-8")
            )

        except (OSError, ValueError, TypeError):

            LOGGER.exception(
                "Failed to send runtime response"
            )
    def _initialize(self) -> None:
        """
        Initialize the request handler.
        """
        self.MAX_MESSAGE_BYTES = self.server.MAX_MESSAGE_BYTES