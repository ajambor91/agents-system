#!/usr/bin/env python3
"""Host broker between Redis Streams and agent-side listeners."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import fcntl
import inspect
import json
import os
import signal
import socket
import struct
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ResponseError


DEFAULT_SOCKET_PATH = "/tmp/comm_runtime.sock"
DEFAULT_REDIS_URL = "redis://localhost:6380"
DEFAULT_DATA_URL = "http://localhost:3000"
ALLOWED_ROLES = {"receiver"}


def acquire_runtime_lock(socket_path: str) -> int | None:
    """Hold one process-wide lock for a runtime socket until the fd is closed."""
    descriptor = os.open(f"{socket_path}.lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    os.ftruncate(descriptor, 0)
    os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
    return descriptor


@dataclass
class Client:
    name: str
    role: str = "anonymous"
    uid: int | None = None
    topics: set[str] = field(default_factory=set)
    write_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CommRuntimeServer:
    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        *,
        redis_url: str = DEFAULT_REDIS_URL,
        data_url: str = DEFAULT_DATA_URL,
        group: str = "communication-runtime",
        retry_seconds: float = 5.0,
    ) -> None:
        self.socket_path = socket_path
        self.redis_url = redis_url
        self.data_url = data_url.rstrip("/")
        self.group = group
        self.consumer = "host-runtime"
        self.retry_seconds = retry_seconds
        self.clients: dict[asyncio.StreamWriter, Client] = {}
        self.server: asyncio.AbstractServer | None = None
        self._stop_event = asyncio.Event()
        self._topic_tasks: dict[str, asyncio.Task[None]] = {}
        self._client_tasks: set[asyncio.Task[None]] = set()
        self._socket_inode: int | None = None
        self._delivery_acks: dict[
            tuple[str, str, asyncio.StreamWriter], asyncio.Future[None]
        ] = {}

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.add(task)
        client = Client(name=f"anonymous-{id(writer)}", uid=self._peer_uid(writer))
        self.clients[writer] = client
        try:
            while not self._stop_event.is_set():
                raw = await reader.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("{"):
                    await self._handle_json(client, writer, line)
                else:
                    await self._handle_control(client, writer, line)
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            self.clients.pop(writer, None)
            writer.close()
            if client.role != "anonymous" and not self._stop_event.is_set():
                print(
                    f"[runtime] disconnected {client.role}:{client.name}",
                    flush=True,
                )
            if task is not None:
                self._client_tasks.discard(task)

    async def _handle_json(
        self, client: Client, writer: asyncio.StreamWriter, line: str
    ) -> None:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            await self._send_json(writer, client, {"ok": False, "error": "invalid_json"})
            return
        if not isinstance(request, dict):
            await self._send_json(writer, client, {"ok": False, "error": "invalid_request"})
            return

        operation = request.get("op")
        if operation == "register":
            await self._register(client, writer, request)
        elif operation == "ack":
            await self._accept_delivery_ack(client, writer, request)
        elif operation == "ping":
            await self._send_json(writer, client, {"ok": True, "op": "pong"})
        else:
            await self._send_json(writer, client, {"ok": False, "error": "unknown_op"})

    async def _accept_delivery_ack(
        self, client: Client, writer: asyncio.StreamWriter, request: dict[str, Any]
    ) -> None:
        if client.role != "receiver":
            await self._send_json(
                writer, client, {"ok": False, "error": "receiver_role_required"}
            )
            return
        event_id = request.get("eventId")
        topic = request.get("topic")
        if not isinstance(event_id, str) or not event_id or not isinstance(topic, str):
            await self._send_json(writer, client, {"ok": False, "error": "invalid_event_id"})
            return
        acknowledgement = self._delivery_acks.get((topic, event_id, writer))
        if acknowledgement is not None and not acknowledgement.done():
            acknowledgement.set_result(None)

    async def _register(
        self, client: Client, writer: asyncio.StreamWriter, request: dict[str, Any]
    ) -> None:
        role = request.get("role")
        name = request.get("name")
        topics = request.get("topics", [])
        if role not in ALLOWED_ROLES:
            await self._send_json(writer, client, {"ok": False, "error": "invalid_role"})
            return
        if not isinstance(name, str) or not name.strip():
            await self._send_json(writer, client, {"ok": False, "error": "invalid_name"})
            return
        if not isinstance(topics, list) or not all(
            isinstance(topic, str) and topic.strip() for topic in topics
        ):
            await self._send_json(writer, client, {"ok": False, "error": "invalid_topics"})
            return

        client.role = role
        client.name = name.strip()
        client.topics = {topic.strip() for topic in topics}
        if role == "receiver" and not client.topics:
            client.topics.add(client.name)
        if role == "receiver":
            for topic in client.topics:
                self._ensure_topic_consumer(topic)
        print(
            f"[runtime] registered {role}:{client.name} "
            f"topics={','.join(sorted(client.topics)) or '-'}",
            flush=True,
        )
        await self._send_json(
            writer,
            client,
            {"ok": True, "op": "registered", "role": role, "name": client.name},
        )

    def _ensure_topic_consumer(self, topic: str) -> None:
        existing = self._topic_tasks.get(topic)
        if existing is not None and not existing.done():
            return
        task = asyncio.create_task(self._consume_topic(topic))
        self._topic_tasks[topic] = task

    async def _consume_topic(self, topic: str) -> None:
        stream = f"stream:{topic}"
        client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        try:
            group_ready = False
            while not self._stop_event.is_set():
                try:
                    if not group_ready:
                        try:
                            await client.xgroup_create(
                                stream, self.group, id="0-0", mkstream=True
                            )
                        except ResponseError as exc:
                            if "BUSYGROUP" not in str(exc):
                                raise
                        group_ready = True
                    pending = await client.xreadgroup(
                        self.group,
                        self.consumer,
                        {stream: "0"},
                        count=10,
                    )
                    if any(messages for _name, messages in pending):
                        events = pending
                    else:
                        events = await client.xreadgroup(
                            self.group,
                            self.consumer,
                            {stream: ">"},
                            count=10,
                            block=5000,
                        )
                    for _stream, messages in events:
                        for event_id, event in messages:
                            acknowledged = await self._dispatch_stream_event(
                                topic, event_id, event
                            )
                            if acknowledged:
                                await client.xack(stream, self.group, event_id)
                            else:
                                await asyncio.sleep(self.retry_seconds)
                                break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print(
                        f"[runtime] stream {stream} error: {exc}; "
                        f"retry in {self.retry_seconds:g}s",
                        file=sys.stderr,
                        flush=True,
                    )
                    await asyncio.sleep(self.retry_seconds)
        finally:
            close = getattr(client, "aclose", None) or client.close
            result = close()
            if inspect.isawaitable(result):
                await result

    async def _dispatch_stream_event(
        self, topic: str, event_id: str, event: dict[str, str]
    ) -> bool:
        message_id = event.get("messageId")
        if not message_id:
            print(f"[runtime] dropping event {event_id} without messageId", file=sys.stderr)
            return True
        try:
            message = await asyncio.to_thread(self._fetch_message, message_id)
        except Exception as exc:
            print(
                f"[runtime] cannot resolve message {message_id}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return False
        envelope = {
            "eventId": event_id,
            "action": event.get("action", "UNKNOWN"),
            "messageId": message_id,
            "topic": topic,
            "message": message,
        }
        delivered = await self._deliver(envelope, {topic}, wait_for_ack=True)
        print(
            f"[runtime] message={message_id} topic={topic} delivered={delivered}",
            flush=True,
        )
        return delivered > 0

    def _fetch_message(self, message_id: str) -> dict[str, Any]:
        url = f"{self.data_url}/api/messages/{message_id}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(str(exc)) from exc
        if not isinstance(value, dict) or value.get("id") != message_id:
            raise RuntimeError("app-data returned an invalid message")
        return value

    async def _deliver(
        self,
        envelope: dict[str, Any],
        receivers: set[str],
        *,
        wait_for_ack: bool = False,
    ) -> int:
        targets = [
            (writer, client)
            for writer, client in list(self.clients.items())
            if client.role == "receiver"
            and ("all" in receivers or bool(client.topics & receivers))
        ]
        delivered = 0
        payload = {"ok": True, "op": "message", "envelope": envelope}
        event_id = envelope.get("eventId")
        topic = envelope.get("topic")
        acknowledgements: list[tuple[asyncio.StreamWriter, asyncio.Future[None]]] = []
        for writer, client in targets:
            try:
                if wait_for_ack:
                    if (
                        not isinstance(event_id, str)
                        or not event_id
                        or not isinstance(topic, str)
                    ):
                        raise RuntimeError("stream envelope is missing eventId or topic")
                    acknowledgement = asyncio.get_running_loop().create_future()
                    self._delivery_acks[(topic, event_id, writer)] = acknowledgement
                    acknowledgements.append((writer, acknowledgement))
                await self._send_json(writer, client, payload)
                if not wait_for_ack:
                    delivered += 1
            except (ConnectionError, OSError):
                self.clients.pop(writer, None)
        if not acknowledgements:
            return delivered
        try:
            done, _pending = await asyncio.wait(
                [future for _writer, future in acknowledgements],
                timeout=15,
                return_when=asyncio.FIRST_COMPLETED,
            )
            delivered = 1 if any(
                not future.cancelled() and future.exception() is None
                for future in done
            ) else 0
        finally:
            for target_writer, future in acknowledgements:
                self._delivery_acks.pop((topic, event_id, target_writer), None)
                if not future.done():
                    future.cancel()
        return delivered

    async def _handle_control(
        self, client: Client, writer: asyncio.StreamWriter, command: str
    ) -> None:
        if command == "PING":
            await self._send_line(writer, client, "PONG")
        elif command == "CLIENTS":
            clients = [
                f"{item.role}:{item.name}"
                for item in self.clients.values()
                if item.role != "anonymous"
            ]
            await self._send_line(writer, client, json.dumps(clients))
        elif command == "STOP":
            if client.uid not in {0, os.geteuid()}:
                await self._send_line(writer, client, "ERROR: STOP is restricted")
            else:
                await self._send_line(writer, client, "SHUTTING DOWN")
                self._stop_event.set()
        else:
            await self._send_line(writer, client, "ERROR: Unknown command")

    @staticmethod
    async def _send_line(
        writer: asyncio.StreamWriter, client: Client, value: str
    ) -> None:
        async with client.write_lock:
            writer.write(f"{value}\n".encode("utf-8"))
            await writer.drain()

    async def _send_json(
        self, writer: asyncio.StreamWriter, client: Client, value: dict[str, Any]
    ) -> None:
        await self._send_line(
            writer, client, json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _peer_uid(writer: asyncio.StreamWriter) -> int | None:
        peer_socket = writer.get_extra_info("socket")
        if peer_socket is None or not hasattr(socket, "SO_PEERCRED"):
            return None
        try:
            credentials = peer_socket.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
            )
            _pid, uid, _gid = struct.unpack("3i", credentials)
            return uid
        except OSError:
            return None

    async def start(self) -> None:
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        self.server = await asyncio.start_unix_server(
            self.handle_client, self.socket_path
        )
        os.chmod(self.socket_path, 0o666)
        self._socket_inode = os.stat(self.socket_path).st_ino
        print(f"[runtime] listening on {self.socket_path}", flush=True)
        try:
            await self._stop_event.wait()
        finally:
            self.server.close()
            writers = list(self.clients)
            for writer in writers:
                writer.close()
            client_tasks = list(self._client_tasks)
            for task in client_tasks:
                task.cancel()
            if client_tasks:
                await asyncio.gather(*client_tasks, return_exceptions=True)
            await self.server.wait_closed()
            for acknowledgement in self._delivery_acks.values():
                if not acknowledgement.done():
                    acknowledgement.cancel()
            for task in self._topic_tasks.values():
                task.cancel()
            if self._topic_tasks:
                await asyncio.gather(*self._topic_tasks.values(), return_exceptions=True)
            with contextlib.suppress(FileNotFoundError):
                if os.stat(self.socket_path).st_ino == self._socket_inode:
                    os.remove(self.socket_path)


async def send_control(socket_path: str, command: str) -> str:
    if not os.path.exists(socket_path):
        return "ERROR: Runtime nie działa (brak gniazda)."
    try:
        reader, writer = await asyncio.open_unix_connection(socket_path)
        writer.write(f"{command}\n".encode("utf-8"))
        await writer.drain()
        response = await reader.readline()
        writer.close()
        return response.decode("utf-8", errors="replace").strip()
    except OSError as exc:
        return f"ERROR: Runtime socket is unavailable: {exc}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="comm_runtime")
    parser.add_argument("action", choices=("start", "status", "stop", "clients"))
    parser.add_argument(
        "--socket",
        default=None,
    )
    parser.add_argument(
        "--redis-url", default=DEFAULT_REDIS_URL
    )
    parser.add_argument(
        "--data-url", default=None
    )
    parser.add_argument(
        "--consumer-group",
        default="communication-runtime",
    )
    parser.add_argument("--retry-seconds", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    from shared.configuration import ApplicationEnvironment

    repository_root = Path(__file__).resolve().parents[2]
    configuration = ApplicationEnvironment.discover(repository_root)
    args = build_parser().parse_args(argv)
    args.socket = configuration.select("AGENTS_DATA_RUNTIME_PATH", flag=args.socket)
    args.data_url = configuration.select("AGENTS_DATA_COMMUNICATION_APP", flag=args.data_url)
    if args.action == "start":
        lock_descriptor = acquire_runtime_lock(args.socket)
        if lock_descriptor is None:
            print("Runtime już działa (aktywna blokada singletona).")
            return 1
        try:
            if os.path.exists(args.socket):
                response = asyncio.run(send_control(args.socket, "PING"))
                if response == "PONG":
                    print("Runtime już działa. Użyj status lub stop.")
                    return 1
                with contextlib.suppress(OSError):
                    os.remove(args.socket)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            asyncio.run(
                CommRuntimeServer(
                    args.socket,
                    redis_url=args.redis_url,
                    data_url=args.data_url,
                    group=args.consumer_group,
                    retry_seconds=args.retry_seconds,
                ).start()
            )
            return 0
        finally:
            os.close(lock_descriptor)

    response = asyncio.run(
        send_control(
            args.socket,
            {"status": "PING", "stop": "STOP", "clients": "CLIENTS"}[args.action],
        )
    )
    if args.action == "status":
        print("Status: DZIAŁA" if response == "PONG" else f"Status: {response}")
        return 0 if response == "PONG" else 1
    if args.action == "clients":
        try:
            clients = json.loads(response)
        except json.JSONDecodeError:
            print(f"Błąd odczytu: {response}")
            return 1
        print("Podpięte aplikacje:")
        for client in clients:
            print(f" - {client}")
        return 0
    print(response)
    return 0 if not response.startswith("ERROR:") else 1


if __name__ == "__main__":
    raise SystemExit(main())
