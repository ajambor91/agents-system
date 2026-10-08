"""UTF-8 JSON messages delimited by a newline."""
from __future__ import annotations

import logging

import json

from .abstract import AbstractMessageCodec
from .models import Response, Request
from .exceptions import UnixSocketProtocolException, UnixSocketSerializationException

LOGGER = logging.getLogger(__name__)


class MessageCodec(AbstractMessageCodec[Request, Response]):
    def encode_request(self, request: Request) -> bytes:
        try:
            return (json.dumps(dict(request.to_mapping()), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise UnixSocketSerializationException(str(exc)) from exc

    def decode_response(self, frame: bytes) -> Response:
        if not frame.endswith(b"\n") or b"\n" in frame[:-1]:
            raise UnixSocketProtocolException("Expected one newline-delimited JSON frame")
        try:
            document = json.loads(frame.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise UnixSocketSerializationException(str(exc)) from exc
        if not isinstance(document, dict) or type(document.get("successful")) is not bool or not isinstance(document.get("request_id"), str):
            LOGGER.warning("Invalid IPC response: missing or invalid request_id/successful fields")
            raise UnixSocketProtocolException("Response requires request_id and boolean successful")
     
        error = document.get("error")
        if error is not None and not isinstance(error, dict):
            raise UnixSocketProtocolException("Response error must be an object")
        if not document["successful"] and error is None:
            raise UnixSocketProtocolException("Failed response requires an error object")
        return Response(document["request_id"], document["successful"], document.get("result"), error)
