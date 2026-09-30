"""Resident runtime with a local JSON-over-Unix-socket API.

The runtime is the owner of application instances and shared services.
Only explicitly registered actions can be invoked through the socket.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import signal
import socket
import socketserver
import stat
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
MAX_MESSAGE_BYTES = 1024 * 1024


class RuntimeProtocolError(Exception):
    def __init__(self, code: str, message: str, *, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


class ClassManager:
    """Hold references to class objects, not instances."""

    def __init__(self) -> None:
        self._classes: dict[str, type] = {}
        self._lock = threading.RLock()

    def register(self, name: str, cls: type) -> None:
        if not inspect.isclass(cls):
            raise TypeError(f"{name} is not a class")
        with self._lock:
            if name in self._classes:
                raise ValueError(f"Class already registered: {name}")
            self._classes[name] = cls

    def get(self, name: str) -> type:
        with self._lock:
            return self._classes[name]

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._classes)


class _RuntimeRequestHandler(socketserver.StreamRequestHandler):
    """One newline-delimited JSON request per connection."""

    def handle(self) -> None:
        self.connection.settimeout(15)
        try:
            raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
            if len(raw) > MAX_MESSAGE_BYTES:
                raise RuntimeProtocolError("REQUEST_TOO_LARGE", "Request exceeds 1 MiB")
            if not raw or not raw.endswith(b"\n"):
                raise RuntimeProtocolError("INVALID_REQUEST", "Expected newline-terminated JSON")
            try:
                request = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise RuntimeProtocolError("INVALID_JSON", "Invalid JSON request") from exc
            if not isinstance(request, dict):
                raise RuntimeProtocolError("INVALID_REQUEST", "JSON request must be an object")
            response = {"ok": True, "result": self.server.runtime.dispatch(request)}
        except RuntimeProtocolError as exc:
            response = {"ok": False, "error": {"code": exc.code, "message": str(exc)}}
            if exc.details is not None:
                response["error"]["details"] = exc.details
        except (socket.timeout, TimeoutError):
            response = {"ok": False, "error": {"code": "TIMEOUT", "message": "Request timed out"}}
        except Exception:
            LOGGER.exception("Unhandled runtime request failure")
            response = {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal runtime error"}}

        try:
            serialized = json.dumps(response, ensure_ascii=False, allow_nan=False)
            self.wfile.write((serialized + "\n").encode("utf-8"))
        except (OSError, ValueError, TypeError):
            LOGGER.exception("Failed to send runtime response")


class _UnixRuntimeServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, path: str, runtime: MainRuntime):
        self.runtime = runtime
        super().__init__(path, _RuntimeRequestHandler)


class MainRuntime:
    """Own initialized applications, shared services, and the resident socket."""

    def __init__(
        self,
        configuration: type | object,
        app_instances: Mapping[str, object],
        manifests: object,
        shared_api: object,
        *,
        socket_path: str | Path = "/run/agents-system/runtime.sock",
        socket_mode: int = 0o600,
    ) -> None:
        self._configuration = configuration
        self._services: dict[str, object] = {}
        self._applications = dict(app_instances)  # Same instances, only a new dict.
        self._actions: dict[tuple[str, str], Callable[[dict[str, Any]], Any]] = {}
        self._app_locks: dict[str, threading.RLock] = {}
        self._lock = threading.RLock()
        self._manifest_lock = threading.RLock()
        self._classes = ClassManager()
        self._socket_path = Path(socket_path)
        self._socket_mode = socket_mode
        self._server: _UnixRuntimeServer | None = None
        self._running = False
        self._initialize(manifests, shared_api)
        self.run()

    def _initialize(self, manifests: object, shared_api: object) -> None:
        self.register_service("class-manager", self._classes)
        self.register_service("manifests", manifests)
        self.register_service("shared-api", shared_api)
        if inspect.isclass(self._configuration):
            self._classes.register("configuration", self._configuration)
        else:
            self.register_service("configuration", self._configuration)
        for name in self._applications:
            self._app_locks[name] = threading.RLock()

    def register_service(self, name: str, instance: object) -> None:
        with self._lock:
            if name in self._services or name in self._applications:
                raise ValueError(f"Name already registered: {name}")
            self._services[name] = instance

    def get_service(self, name: str) -> object:
        with self._lock:
            return self._services[name]

    def get_application(self, name: str) -> object:
        with self._lock:
            return self._applications[name]

    def get_class(self, name: str) -> type:
        return self._classes.get(name)

    def register_action(
        self,
        module_name: str,
        action_name: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Explicitly expose one operation through the socket.

        Handler receives request['payload'] and should return JSON-compatible data.
        Operations for the same application are serialized by its RLock.
        """
        if not callable(handler):
            raise TypeError("Action handler must be callable")
        with self._lock:
            if module_name not in self._applications:
                raise KeyError(f"Application not registered: {module_name}")
            key = (module_name, action_name)
            if key in self._actions:
                raise ValueError(f"Action already registered: {module_name}.{action_name}")
            self._actions[key] = handler

    @staticmethod
    def _validation_details(exc: Exception) -> list[dict[str, str]] | None:
        errors = getattr(exc, "errors", None)
        if not isinstance(errors, (list, tuple)):
            return None
        return [
            {"path": str(getattr(item, "path", "")), "message": str(getattr(item, "message", item))}
            for item in errors
        ]

    def dispatch(self, request: dict[str, Any]) -> Any:
        action = request.get("action")
        if not isinstance(action, str):
            raise RuntimeProtocolError("INVALID_REQUEST", "'action' must be a string")

        if action == "ping":
            return {"status": "running"}

        if action == "applications.list":
            with self._lock:
                return sorted(self._applications)

        if action == "manifests.validate":
            data = request.get("data")
            if not isinstance(data, dict):
                raise RuntimeProtocolError("INVALID_REQUEST", "'data' must be an object")
            with self._manifest_lock:
                try:
                    self.get_service("manifests").validate_manifest(data)
                except Exception as exc:
                    issues = self._validation_details(exc)
                    if issues is not None:
                        raise RuntimeProtocolError(
                            "VALIDATION_FAILED", "Manifest validation failed", details=issues
                        ) from exc
                    raise
            return {"valid": True}

        if action == "application.call":
            module = request.get("module")
            method = request.get("method")
            payload = request.get("payload", {})
            if not isinstance(module, str) or not isinstance(method, str):
                raise RuntimeProtocolError("INVALID_REQUEST", "'module' and 'method' must be strings")
            if not isinstance(payload, dict):
                raise RuntimeProtocolError("INVALID_REQUEST", "'payload' must be an object")
            with self._lock:
                handler = self._actions.get((module, method))
                app_lock = self._app_locks.get(module)
            if handler is None or app_lock is None:
                raise RuntimeProtocolError("UNKNOWN_ACTION", "Application action is not available")
            with app_lock:
                return handler(payload)

        raise RuntimeProtocolError("UNKNOWN_ACTION", "Unknown runtime action")
    def run(self):
        self.socket_server.serve_forever() 
    # def run(self) -> None:
        
    #     """Block in the current process until SIGTERM/SIGINT or stop()."""
    #     with self._lock:
    #         if self._running:
    #             raise RuntimeError("Runtime server is already running")
    #         self._socket_path.parent.mkdir(parents=True, exist_ok=True)
    #         if self._socket_path.exists():
    #             raise FileExistsError(
    #                 f"Socket path already exists: {self._socket_path}. "
    #                 "Check whether another runtime is running."
    #             )
    #         self._server = _UnixRuntimeServer(str(self._socket_path), self)
    #         os.chmod(self._socket_path, self._socket_mode)
    #         socket_inode = self._socket_path.stat().st_ino
    #         self._running = True

    #     old_handlers: dict[int, Any] = {}
    #     if threading.current_thread() is threading.main_thread():
    #         def handle_signal(signum: int, frame: Any) -> None:
    #             # socketserver.shutdown() cannot run in the serve_forever thread.
    #             threading.Thread(target=self.stop, daemon=True).start()

    #         for signum in (signal.SIGINT, signal.SIGTERM):
    #             old_handlers[signum] = signal.getsignal(signum)
    #             signal.signal(signum, handle_signal)
    #     try:
    #         LOGGER.info("Runtime listening at %s", self._socket_path)
    #         self._server.serve_forever(poll_interval=0.2)
    #     finally:
    #         with self._lock:
    #             self._running = False
    #             self._server.server_close()
    #             self._server = None
    #         try:
    #             st = self._socket_path.lstat()
    #             if stat.S_ISSOCK(st.st_mode) and st.st_ino == socket_inode:
    #                 self._socket_path.unlink()
    #         except FileNotFoundError:
    #             pass
    #         for signum, previous in old_handlers.items():
    #             signal.signal(signum, previous)

    def stop(self) -> None:
        with self._lock:
            server = self._server if self._running else None
        if server is not None:
            server.shutdown()


class RuntimeClient:
    """Used by another process, e.g. CLI or installer."""

    def __init__(
        self,
        socket_path: str | Path = "/run/agents-system/runtime.sock",
        *,
        timeout: float = 10,
    ) -> None:
        self._socket_path = str(socket_path)
        self._timeout = timeout

    def request(self, action: str, **kwargs: Any) -> Any:
        request = json.dumps({"action": action, **kwargs}, ensure_ascii=False)
        encoded = (request + "\n").encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise ValueError("Request exceeds 1 MiB")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self._timeout)
            sock.connect(self._socket_path)
            sock.sendall(encoded)
            with sock.makefile("rb") as stream:
                raw = stream.readline(MAX_MESSAGE_BYTES + 1)
        if not raw or len(raw) > MAX_MESSAGE_BYTES or not raw.endswith(b"\n"):
            raise ConnectionError("Invalid or oversized runtime response")
        response = json.loads(raw)
        if not response.get("ok"):
            error = response.get("error", {})
            raise RuntimeProtocolError(
                error.get("code", "UNKNOWN_ERROR"),
                error.get("message", "Unknown runtime error"),
                details=error.get("details"),
            )
        return response["result"]
