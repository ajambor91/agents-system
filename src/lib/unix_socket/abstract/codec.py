"""Abstract serialization and framing contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..models import Request, Response

RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)


class AbstractMessageCodec(ABC, Generic[RequestT, ResponseT]):
    """Translate typed models to and from protocol frames.

    Concrete codecs define serialization and framing. A decoder must reject
    incomplete, oversized and structurally invalid frames.
    """

    @abstractmethod
    def encode_request(self, request: RequestT) -> bytes:
        """Validate and serialize a request into exactly one outbound frame."""

    @abstractmethod
    def decode_response(self, frame: bytes) -> ResponseT:
        """Deserialize one complete inbound frame into a response model."""

