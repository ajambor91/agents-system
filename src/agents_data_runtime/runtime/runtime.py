from __future__ import annotations
import os
import logging
from typing import Any
from lib.configuration import Configuration
from ..app import Application
from .runtime_dispatcher import RuntimeDispatcher
from .runtime_server import RuntimeServer
import threading
import os
import signal
import stat
import threading
from pathlib import Path
LOGGER = logging.getLogger(__name__)

class Runtime:
    _configuration: Configuration
    _application: Application
    _socket_path: str
    _socket_mode: int
    def __init__(self, configuration: Configuration, app: Application):
        self._application = app
        self._configuration = configuration 
        settings = type(configuration)
        socket_path: str = settings.SYSTEM_AGENT_MANAGER_RUNTIME_SOCKET
        socket_mode: int = 0o600        
        max_message_base = int(
            settings.MAX_MESSAGE_BYTES_BASE
        )
        max_message_multiplier = int(
            settings.MAX_MESSAGE_BYTES_MULTIPLIER
        )
        
        max_message_bytes = (
            max_message_base * max_message_multiplier
        )
        
        if max_message_bytes > 0:
            self.MAX_MESSAGE_BYTES = (
                max_message_bytes
            )
        
        self._lock = threading.RLock()
        
        self._socket_path = Path(
            socket_path
        )
        
        self._socket_mode = socket_mode

        self._dispatcher = RuntimeDispatcher(
            self._application
        )
        
        self._server: RuntimeServer | None = None
        
        self._running = False
    
    def dispatch(
        self,
        request: dict[str, Any],
    ) -> Any:
        """
        Dispatch request through RuntimeDispatcher.
        """

        return self._dispatcher.dispatch(
            request
        )

    def run(self) -> None:
        """
        Block in the current process until SIGTERM,
        SIGINT or stop().
        """

        LOGGER.info("Starting shared runtime: socket=%s maximum_message_bytes=%s", self._socket_path, self.MAX_MESSAGE_BYTES)
        with self._lock:

            if self._running:

                raise RuntimeError(
                    "Runtime server is already running"
                )

            self._socket_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if self._socket_path.exists():

                raise FileExistsError(
                    "Socket path already exists: "
                    f"{self._socket_path}. "
                    "Check whether another runtime "
                    "is running."
                )

            self._server = RuntimeServer(
                str(self._socket_path),
                self,
                self.MAX_MESSAGE_BYTES,
            )

            os.chmod(
                self._socket_path,
                self._socket_mode,
            )
            
            socket_inode = (
                self._socket_path
                .stat()
                .st_ino
            )

            self._running = True

        old_handlers: dict[int, Any] = {}

        if (
            threading.current_thread()
            is threading.main_thread()
        ):

            def handle_signal(
                signum: int,
                frame: Any,
            ) -> None:

                threading.Thread(
                    target=self.stop,
                    daemon=True,
                    name="runtime-stop",
                ).start()

            for signum in (
                signal.SIGINT,
                signal.SIGTERM,
            ):

                old_handlers[signum] = (
                    signal.getsignal(
                        signum
                    )
                )

                signal.signal(
                    signum,
                    handle_signal,
                )

        try:

            LOGGER.info(
                "Runtime listening at %s",
                self._socket_path,
            )

            assert self._server is not None

            self._server.serve_forever(
                poll_interval=0.2
            )

        finally:

            with self._lock:

                self._running = False

                if self._server is not None:

                    self._server.server_close()

                self._server = None

            self._dispatcher.shutdown(
                wait=True
            )

            try:

                st = (
                    self._socket_path
                    .lstat()
                )

                if (
                    stat.S_ISSOCK(
                        st.st_mode
                    )
                    and st.st_ino
                    == socket_inode
                ):

                    self._socket_path.unlink()

            except FileNotFoundError:
                pass

            LOGGER.info("Shared runtime stopped: socket=%s", self._socket_path)

            for signum, previous in (
                old_handlers.items()
            ):

                signal.signal(
                    signum,
                    previous,
                )

    def stop(self) -> None:

        LOGGER.info("Stopping shared runtime: socket=%s", self._socket_path)
        with self._lock:

            server = (
                self._server
                if self._running
                else None
            )

        if server is not None:
            server.shutdown()