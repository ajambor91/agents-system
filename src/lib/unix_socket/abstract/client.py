"""Abstract high-level client contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .codec import AbstractMessageCodec
from .transport import AbstractUnixSocketTransport
from ..abstract.models import  AbstractSocketConfiguration
from ..models import Request, Response
RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)


class AbstractUnixSocketClient(ABC, Generic[RequestT, ResponseT]):
    """Coordinate request validation, encoding, transport and decoding.

    A concrete client should receive its codec and transport as dependencies.
    It should not hide retries: once bytes have been written, repeating a
    mutating request may execute the operation twice.
    """

    @abstractmethod
    def __init__(self, configuration: AbstractSocketConfiguration, codec: AbstractMessageCodec, transport: AbstractUnixSocketTransport) -> None:
        """Bind application configuration, codec and transport."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the underlying transport currently has a connection."""

    @abstractmethod
    def connect(self) -> None:
        """Open the configured Unix socket connection."""

    @abstractmethod
    def request(self, request: RequestT, *, timeout: float | None = None) -> ResponseT:
        """Send one typed request and return its matching typed response."""

    @abstractmethod
    def close(self) -> None:
        """Close the transport safely; repeated calls should be harmless."""

