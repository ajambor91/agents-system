"""Resident runtime with a local JSON-over-Unix-socket API.

The runtime owns access to managed application instances.
Only explicitly registered methods can be invoked through the socket.
"""

from __future__ import annotations

import logging
import os
import signal
import stat
import threading

from pathlib import Path
from typing import Any

from lib.configuration import Configuration
from . import InstanceManager
from . import RuntimeDispatcher
from . import RuntimeServer


LOGGER = logging.getLogger(__name__)


class MainRuntime:
    """
    Runtime for managed application instances.

    InstanceManager is the source of truth for available
    application/service instances.

    RuntimeDispatcher owns execution threads.
    """

    MAX_MESSAGE_BYTES = 1024 * 1024

    configuration: Configuration = None

    def __init__(
        self,
        instance_manager: InstanceManager,
        configuration: Configuration,
    ) -> None:

        settings = type(configuration)
        socket_path: str = settings.SYSTEM_AGENT_RUNTIME_SOCKET
        socket_mode: int = 0o600
        self._instance_manager = instance_manager
        self.configuration = configuration

        max_message_base = int(
            settings.MAX_MESSAGE_BYTES_BASE
        )

        max_message_multiplier = int(
            settings.MAX_MESSAGE_BYTES_MULTIPLIER
        )

        max_message_bytes = (
            max_message_base
            * max_message_multiplier
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
            self._instance_manager
        )

        self._server: RuntimeServer | None = None

        self._running = False

    def get_service(
        self,
        name: str,
    ) -> object:
        """
        Return the actual managed instance.
        """

        return (
            self._instance_manager
            .get(name)
            .instance
        )

    def register_action(
        self,
        service_name: str,
        method_name: str,
    ) -> None:
        """
        Expose a managed instance method to the runtime API.
        """

        self._dispatcher.register_action(
            service_name,
            method_name,
        )

    def register_actions(
        self,
        service_name: str,
        methods: list[str],
    ) -> None:

        self._dispatcher.register_actions(
            service_name,
            methods,
        )

    def refresh_services(
        self,
    ) -> None:
        """
        Synchronize runtime execution threads
        with InstanceManager.
        """

        self._dispatcher.refresh_instances()

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

            for signum, previous in (
                old_handlers.items()
            ):

                signal.signal(
                    signum,
                    previous,
                )

    def stop(self) -> None:

        with self._lock:

            server = (
                self._server
                if self._running
                else None
            )

        if server is not None:
            server.shutdown()