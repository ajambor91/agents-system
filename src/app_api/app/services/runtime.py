"""Shared runtime client for the app_api application layer."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from ..models import ApiError, ApiResult
from shared.configuration import ApplicationEnvironment


class RuntimeClient:
    """Invoke app_api inside the shared runtime, with explicit safe fallback."""

    def __init__(self, configuration: ApplicationEnvironment) -> None:
        self.socket_path = Path(configuration.select("APP_RUNTIME_PATH"))

    def execute(self, arguments: list[str]) -> ApiResult | None:
        if not self.socket_path.exists():
            return None
        request = {"module": "app_api", "payload": {"args": arguments}}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(10)
                client.connect(str(self.socket_path))
                client.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
                response = json.loads(client.makefile("r", encoding="utf-8").readline())
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiError(f"Błąd połączenia ze wspólnym runtime: {exc}", exit_code=1) from exc
        if not response.get("ok"):
            if response.get("error_code") == "module_unavailable":
                return None
            raise ApiError(str(response.get("error", "Runtime odrzucił żądanie")), exit_code=1)
        result = response.get("result")
        if not isinstance(result, dict):
            raise ApiError("Runtime zwrócił nieprawidłowy wynik app_api", exit_code=1)
        return ApiResult(
            exit_code=int(result.get("exit_code", 1)),
            stdout=str(result.get("stdout", "")),
            stderr=str(result.get("stderr", "")),
            data=result.get("data"),
        )
