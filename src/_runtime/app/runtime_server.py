
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_runtime import MainRuntime

import socketserver

from .runtime_request_handler import RuntimeRequestHandler

class RuntimeServer(
    socketserver.ThreadingUnixStreamServer
):
    daemon_threads = True
    allow_reuse_address = False
    MAX_MESSAGE_BYTES = None
    def __init__(
        self,
        path: str,
        runtime: MainRuntime,
        max_message_bytes: int = 1024 * 1024,
    ):
        self.runtime = runtime
        self.MAX_MESSAGE_BYTES = max_message_bytes
        super().__init__(
            path,
            RuntimeRequestHandler,
        )