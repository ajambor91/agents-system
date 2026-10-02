"""Abstract serialization and framing contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..abstract.models import AbstractRequest, AbstractResponse

RequestT = TypeVar("RequestT", bound=AbstractRequest)
ResponseT = TypeVar("ResponseT", bound=AbstractResponse)


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

