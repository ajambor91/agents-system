import json
import logging
import socketserver

from .exceptions import RuntimeProtocolError
from .models import Request, Response

LOGGER = logging.getLogger(__name__)


class RuntimeRequestHandler(socketserver.StreamRequestHandler):
    MAX_MESSAGE_BYTES = 1024 * 1024

    def handle(self) -> None:
        self._initialize()
        self.connection.settimeout(15)

        while True:
            try:
                request = self._read_request()

                if request is None:
                    return

                response = self._process(request)

            except RuntimeProtocolError as exc:
                response = Response(
                    request_id=None,
                    successful=False,
                    result=None,
                    error={
                        "code": exc.code,
                        "message": (
                            exc.details
                            if exc.details
                            else str(exc)
                        ),
                    },
                )

            except (TimeoutError, OSError):
                return

            except Exception as exc:
                LOGGER.exception(
                    "Unhandled runtime request failure"
                )

                response = Response(
                    request_id=None,
                    successful=False,
                    result=None,
                    error={
                        "code": "INTERNAL_ERROR",
                        "message": str(exc),
                    },
                )

            try:
                self._send_response(response)

            except OSError:
                LOGGER.exception(
                    "Failed to send runtime response"
                )
                return

    def _read_request(self) -> Request | None:
        raw = self.rfile.readline(
            self.MAX_MESSAGE_BYTES + 1
        )

        if not raw:
            return None

        if len(raw) > self.MAX_MESSAGE_BYTES:
            raise RuntimeProtocolError(
                "REQUEST_TOO_LARGE",
                "Request exceeds maximum size",
            )

        if not raw.endswith(b"\n"):
            raise RuntimeProtocolError(
                "INVALID_REQUEST",
                "Expected newline-terminated JSON",
            )

        try:
            body = json.loads(raw)

        except (ValueError, UnicodeError) as exc:
            raise RuntimeProtocolError(
                "INVALID_JSON",
                "Invalid JSON request",
            ) from exc

        if not isinstance(body, dict):
            raise RuntimeProtocolError(
                "INVALID_REQUEST",
                "JSON request must be an object",
            )

        return Request(body)

    def _process(self, request: Request) -> Response:
        result = self.server.runtime.dispatch(request)

        return Response(
            request_id=request.request_id,
            successful=True,
            result=result,
        )

    def _send_response(self, response: Response) -> None:
        serialized = json.dumps(
            response.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
        )

        self.wfile.write(
            (serialized + "\n").encode("utf-8")
        )

        self.wfile.flush()

    def _initialize(self) -> None:
        self.MAX_MESSAGE_BYTES = (
            self.server.MAX_MESSAGE_BYTES
        )