#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import pwd
import signal
import socket
import struct
import sys

from pathlib import Path
from typing import Any

from lib.configuration import Configuration
from .context import ApplicationContext
from .services.process import ProcessRunner
from .services.wakeup import WakeupService


DEFAULT_SOCKET = "/run/agents-manager/control.sock"
MAX_REQUEST_BYTES = 2 * 1024 * 1024


class GatewayServer:
    """Gateway-owned Unix service accepting authenticated agent wakeups."""

    def __init__(self, context: ApplicationContext, socket_path: Path) -> None:
        self.context = context
        self.socket_path = socket_path
        self.stopping = asyncio.Event()
        self.server: asyncio.AbstractServer | None = None

    async def run(self) -> None:
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
            limit=MAX_REQUEST_BYTES + 1,
        )
        self.socket_path.chmod(0o666)
        print(f"[gateway] listening on {self.socket_path}", flush=True)
        async with self.server:
            await self.stopping.wait()
        self.server.close()
        await self.server.wait_closed()
        self.socket_path.unlink(missing_ok=True)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            caller_user = self._peer_user(writer)
            raw = await reader.readline()
            if len(raw) > MAX_REQUEST_BYTES:
                raise ValueError("Gateway request exceeds 2 MiB.")
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("Gateway request must be an object.")
            action = request.get("action")
            if action == "status":
                response = {"ok": True, "status": "running"}
            elif action == "stop":
                self._require_controller(caller_user)
                response = {"ok": True, "status": "stopping"}
                self.stopping.set()
            elif action == "wakeup":
                response = await self._wakeup(request, caller_user)
            else:
                raise ValueError("Unsupported gateway action.")
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
        writer.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
        with contextlib.suppress(ConnectionError):
            await writer.drain()
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()

    async def _wakeup(
        self, request: dict[str, Any], caller_user: str
    ) -> dict[str, Any]:
        agent = request.get("agent")
        envelope = request.get("envelope")
        timeout = request.get("timeout", 600)
        if not isinstance(agent, str) or not isinstance(envelope, dict):
            raise ValueError("Wakeup requires agent and envelope.")
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise ValueError("Wakeup timeout must be an integer.")
        result = await asyncio.to_thread(
            WakeupService(self.context, ProcessRunner()).execute,
            agent_name=agent,
            envelope=envelope,
            caller_user=caller_user,
            timeout=timeout,
        )
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr, flush=True)
        return {"ok": True, "agent": agent, "output": result.stdout[-4096:]}

    def _require_controller(self, caller_user: str) -> None:
        if caller_user not in {"root", self.context.gateway_user}:
            raise PermissionError("Only root or the gateway user can stop the service.")

    @staticmethod
    def _peer_user(writer: asyncio.StreamWriter) -> str:
        peer = writer.get_extra_info("socket")
        if peer is None:
            raise PermissionError("Cannot authenticate gateway client.")
        _pid, uid, _gid = struct.unpack(
            "3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        return pwd.getpwuid(uid).pw_name


def request(socket_path: Path, action: str) -> dict[str, Any]:
    client = socket.socket(socket.AF_UNIX)
    client.settimeout(5)
    try:
        client.connect(str(socket_path))
        client.sendall((json.dumps({"action": action}) + "\n").encode("utf-8"))
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                break
            raw += chunk
    finally:
        client.close()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Gateway returned an invalid response.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agents-gateway")
    parser.add_argument("action", choices=("serve", "status", "stop"))
    parser.add_argument("--socket", default=DEFAULT_SOCKET)
    return parser


def main(argv: list[str] | None = None, configuration: Configuration | None = None) -> int:
    args = build_parser().parse_args(argv)
    socket_path = Path(args.socket)
    if args.action != "serve":
        try:
            response = request(socket_path, args.action)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response.get("ok") else 1

    repo_root = Path(__file__).resolve().parents[3]
    if configuration is None:
        configured = (
            Path(os.environ["ABSOLUTE_CONFIG_PATH"])
            if "ABSOLUTE_CONFIG_PATH" in os.environ
            else repo_root / "resources" / "app_env.json"
        )
        document = json.loads(configured.read_text(encoding="utf-8"))
        variables = document.get("variables")
        if not isinstance(variables, list):
            raise ValueError(f"{configured}: variables must be a list")
        configuration = Configuration(variables)
    context = ApplicationContext.create(repo_root, configuration=configuration)
    server = GatewayServer(context, socket_path)

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, server.stopping.set)
        await server.run()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
