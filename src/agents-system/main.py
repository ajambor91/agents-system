#!/usr/bin/env python3
"""Resident runtime for Python applications installed into Agents System."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import getpass
import grp
import pwd
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

DEFAULT_ROOT = Path(os.environ.get("AGENTS_SYSTEM_HOME", "/home/user-system/.agents"))
REGISTRY_PATH = DEFAULT_ROOT / "modules.json"
SOCKET_PATH = DEFAULT_ROOT / "runtime.sock"
PID_PATH = DEFAULT_ROOT / "runtime.pid"


class RuntimeErrorMessage(Exception):
    """Expected runtime or module configuration error."""


def read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {"schema_version": 1, "modules": {}}
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeErrorMessage(f"Nieprawidłowy rejestr modułów: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("modules", {}), dict):
        raise RuntimeErrorMessage("Rejestr modułów musi zawierać obiekt modules")
    return value


def write_registry(value: dict[str, Any]) -> None:
    DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(REGISTRY_PATH)


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically write one Agents System JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def discover_entrypoint(repository_path: Path) -> Path:
    manifest_path = repository_path / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entrypoint = manifest.get("application", {}).get("entrypoint")
            if isinstance(entrypoint, str) and entrypoint:
                candidate = repository_path / entrypoint
                if candidate.is_file():
                    return candidate.resolve()
        except (OSError, json.JSONDecodeError):
            pass
    candidates = sorted((repository_path / "src").glob("**/main.py")) if (repository_path / "src").is_dir() else []
    if len(candidates) == 1:
        return candidates[0].resolve()
    raise RuntimeErrorMessage(
        "Nie można wyznaczyć entrypointu; podaj --entrypoint albo popraw application.entrypoint w manifest.json"
    )


def module_record(name: str, repository_path: Path, entrypoint: Path) -> dict[str, Any]:
    return {
        "id": name,
        "repository_path": str(repository_path.resolve()),
        "entrypoint": str(entrypoint.resolve()),
        "status": "registered",
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def load_module(record: dict[str, Any]) -> tuple[ModuleType, Any]:
    entrypoint = Path(str(record["entrypoint"])).resolve()
    if not entrypoint.is_file():
        raise RuntimeErrorMessage(f"Brak entrypointu modułu {record['id']}: {entrypoint}")
    module_name = f"agents_system_module_{record['id'].replace('-', '_')}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, entrypoint)
    if spec is None or spec.loader is None:
        raise RuntimeErrorMessage(f"Nie można załadować modułu: {entrypoint}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    factory = getattr(module, "create_service", None)
    if callable(factory):
        return module, factory()
    handler = getattr(module, "handle", None)
    if callable(handler):
        return module, handler
    application = getattr(module, "Application", None)
    if application is not None and callable(getattr(application, "handle", None)):
        return module, application()
    raise RuntimeErrorMessage(
        f"Moduł {record['id']} nie udostępnia create_service(), handle() ani Application.handle(); "
        "jego wrappery pozostają niezależne, ale nie może działać jako proces RAM"
    )


def call_handler(handler: Any, payload: dict[str, Any]) -> Any:
    if callable(handler):
        return handler(payload)
    raise RuntimeErrorMessage("Załadowany moduł nie ma wywoływalnego handlera")


def runtime_status() -> dict[str, Any]:
    registry = read_registry()
    return {
        "running": PID_PATH.is_file() and SOCKET_PATH.exists(),
        "pid": PID_PATH.read_text(encoding="utf-8").strip() if PID_PATH.is_file() else None,
        "socket": str(SOCKET_PATH),
        "modules": registry.get("modules", {}),
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def system_status() -> dict[str, Any]:
    """Collect a human-oriented snapshot without requiring repo-manifests API."""
    storage_root = Path(os.environ.get("USER_SYSTEM_HOME", "/home/user-system")) / ".repos"
    repositories = _read_jsonl(storage_root / "repos")
    repository_rows: list[dict[str, Any]] = []
    for entry in repositories:
        repository_id = str(entry.get("id") or entry.get("repo_name") or "")
        history_files = sorted((storage_root / "repositories" / repository_id / "history").glob("**/*.jsonl"))
        history = [item for path in history_files for item in _read_jsonl(path)]
        repository_rows.append({
            "id": repository_id,
            "name": entry.get("repo_name") or entry.get("name"),
            "version": entry.get("version", "0.0.1"),
            "status": entry.get("status", "unknown"),
            "system": bool(entry.get("system")),
            "path": entry.get("path"),
            "last_action": entry.get("last_action"),
            "history_count": len(history),
            "history": history[-5:],
        })
    agents: list[dict[str, Any]] = []
    if DEFAULT_ROOT.is_dir():
        try:
            directories = sorted(path for path in DEFAULT_ROOT.iterdir() if path.is_dir())
        except PermissionError:
            directories = []
            agents.append({"id": "-", "path": str(DEFAULT_ROOT), "runtime": {"error": "brak dostępu"}})
        for directory in directories:
            if directory.name in {"__pycache__"}:
                continue
            runtime = {}
            runtime_file = directory / "runtime.json"
            if runtime_file.is_file():
                try:
                    value = json.loads(runtime_file.read_text(encoding="utf-8"))
                    if isinstance(value, dict):
                        runtime = value
                except (OSError, json.JSONDecodeError):
                    runtime = {"error": "niepoprawny lub niedostępny runtime.json"}
            agents.append({"id": directory.name, "path": str(directory), "runtime": runtime})
    return {
        "user": os.environ.get("USER_SYSTEM_USER", "user-system"),
        "home": os.environ.get("USER_SYSTEM_HOME", "/home/user-system"),
        "runtime": runtime_status(),
        "repositories": repository_rows,
        "agents": agents,
    }


def print_system_status(report: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print("Agents System")
    print(f"Użytkownik: {report['user']} | HOME: {report['home']}")
    runtime = report["runtime"]
    print(f"Runtime: {'działa' if runtime['running'] else 'zatrzymany'}")
    print(f"\nRepozytoria ({len(report['repositories'])}):")
    for repository in report["repositories"]:
        print(f"  - {repository['name']} [{repository['status']}] v{repository['version']}")
        print(f"    {repository['path']} | akcja: {repository['last_action'] or '-'} | historia: {repository['history_count']}")
        for action in repository["history"][-3:]:
            print(f"      {action.get('action', '-')} | {action.get('status', '-')} | {action.get('finished_at', action.get('started_at', '-'))}")
    print(f"\nAgenci ({len(report['agents'])}):")
    if not report["agents"]:
        print("  - brak wykrytych katalogów agentów")
    for agent in report["agents"]:
        state = agent["runtime"].get("status", agent["runtime"].get("state", "brak runtime"))
        print(f"  - {agent['id']} [{state}] {agent['path']}")
    return 0


def user_record(username: str) -> dict[str, str]:
    try:
        account = pwd.getpwnam(username)
        group = grp.getgrgid(account.pw_gid).gr_name
    except KeyError as exc:
        raise RuntimeErrorMessage(f"Nie znaleziono użytkownika: {username}") from exc
    return {"name": account.pw_name, "home": account.pw_dir, "group": group, "shell": account.pw_shell}


def create_user(arguments: argparse.Namespace) -> int:
    username = arguments.user
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", username):
        raise RuntimeErrorMessage("Nieprawidłowa nazwa użytkownika")
    if not arguments.yes:
        print(f"Użytkownik {username} otrzyma katalog /home/{username}, repositories i .agents. Użyj --yes, aby potwierdzić.")
        return 2
    if os.geteuid() != 0:
        raise RuntimeErrorMessage("Tworzenie użytkownika wymaga sudo")
    if subprocess.run(["getent", "group", username], capture_output=True).returncode != 0:
        subprocess.run(["groupadd", "--system", username], check=True)
    if subprocess.run(["getent", "passwd", username], capture_output=True).returncode != 0:
        shell = "/usr/sbin/nologin" if Path("/usr/sbin/nologin").exists() else "/sbin/nologin"
        subprocess.run(["useradd", "--system", "--gid", username, "--home-dir", f"/home/{username}", "--create-home", "--shell", shell, username], check=True)
    home = Path(f"/home/{username}")
    for path in (home / "repositories", home / ".agents"):
        path.mkdir(parents=True, exist_ok=True)
    print(json.dumps(user_record(username), ensure_ascii=False))
    return 0


def get_user(arguments: argparse.Namespace) -> int:
    username = arguments.user or os.environ.get("USER_SYSTEM_USER", "user-system")
    record = user_record(username)
    if arguments.home:
        print(record["home"])
    elif arguments.name:
        print(record["name"])
    elif arguments.group:
        print(record["group"])
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def list_users() -> int:
    users = []
    for entry in pwd.getpwall():
        if entry.pw_dir.startswith("/home/") and entry.pw_name != "root":
            users.append(user_record(entry.pw_name))
    print(json.dumps(users, ensure_ascii=False, indent=2))
    return 0


def set_user(arguments: argparse.Namespace) -> int:
    if not arguments.yes:
        print("Ustawienie domyślnego użytkownika zmieni konfigurację Agents System. Użyj --yes, aby potwierdzić.")
        return 2
    record = user_record(arguments.user)
    write_json(DEFAULT_ROOT / "user.json", record)
    print(json.dumps(record, ensure_ascii=False))
    return 0


def serve() -> int:
    DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        raise RuntimeErrorMessage(f"Runtime już działa albo pozostał socket: {SOCKET_PATH}")
    registry = read_registry()
    loaded: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, record in registry.get("modules", {}).items():
        try:
            _, handler = load_module(record)
            loaded[name] = handler
            record["status"] = "loaded"
        except RuntimeErrorMessage as exc:
            errors[name] = str(exc)
            record["status"] = "error"
            record["error"] = str(exc)
    write_registry(registry)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    SOCKET_PATH.chmod(0o660)
    PID_PATH.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    stopping = False

    def stop(_signal: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.listen(16)
    try:
        while not stopping:
            server.settimeout(0.5)
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                raw = connection.makefile("r", encoding="utf-8").readline()
                try:
                    request = json.loads(raw)
                    if request.get("action") == "status":
                        response = {"ok": True, "status": runtime_status(), "load_errors": errors}
                    else:
                        name = str(request.get("module", ""))
                        if name not in loaded:
                            raise RuntimeErrorMessage(errors.get(name, f"Moduł nie jest załadowany: {name}"))
                        response = {"ok": True, "result": call_handler(loaded[name], request.get("payload", {}))}
                except (RuntimeErrorMessage, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    response = {"ok": False, "error": str(exc)}
                connection.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        server.close()
        SOCKET_PATH.unlink(missing_ok=True)
        PID_PATH.unlink(missing_ok=True)
    return 0


def start_runtime() -> int:
    if SOCKET_PATH.exists() or PID_PATH.exists():
        print(json.dumps(runtime_status(), ensure_ascii=False))
        return 0
    child = os.fork()
    if child:
        print(json.dumps({"started": True, "pid": child, "socket": str(SOCKET_PATH)}, ensure_ascii=False))
        return 0
    os.setsid()
    try:
        raise SystemExit(serve())
    except Exception as exc:
        print(f"Agents System runtime: {exc}", file=sys.stderr)
        raise SystemExit(1)


def stop_runtime() -> int:
    if not PID_PATH.is_file():
        print(json.dumps({"stopped": False, "reason": "runtime nie działa"}, ensure_ascii=False))
        return 0
    pid = int(PID_PATH.read_text(encoding="utf-8"))
    os.kill(pid, signal.SIGTERM)
    print(json.dumps({"stopped": True, "pid": pid}, ensure_ascii=False))
    return 0


def add_module(arguments: argparse.Namespace) -> int:
    repository_path = Path(arguments.repository_path).expanduser().resolve() if arguments.repository_path else (
        DEFAULT_ROOT.parent / "repositories" / arguments.name
    ).resolve()
    if not repository_path.is_dir():
        raise RuntimeErrorMessage(f"Brak katalogu repozytorium: {repository_path}")
    entrypoint = Path(arguments.entrypoint).expanduser().resolve() if arguments.entrypoint else discover_entrypoint(repository_path)
    registry = read_registry()
    registry.setdefault("modules", {})[arguments.name] = module_record(arguments.name, repository_path, entrypoint)
    write_registry(registry)
    if arguments.start:
        start_runtime()
    print(json.dumps({"registered": arguments.name, "entrypoint": str(entrypoint)}, ensure_ascii=False))
    return 0


def remove_module(arguments: argparse.Namespace) -> int:
    registry = read_registry()
    if registry.get("modules", {}).pop(arguments.name, None) is None:
        raise RuntimeErrorMessage(f"Nie ma zarejestrowanego modułu: {arguments.name}")
    write_registry(registry)
    print(json.dumps({"removed": arguments.name}, ensure_ascii=False))
    return 0


def call_module(arguments: argparse.Namespace) -> int:
    if not SOCKET_PATH.exists():
        raise RuntimeErrorMessage("Runtime nie działa; uruchom asystem_runtime_start")
    request = {"module": arguments.name, "payload": json.loads(arguments.payload)}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(SOCKET_PATH))
        client.sendall((json.dumps(request) + "\n").encode("utf-8"))
        response = json.loads(client.makefile("r", encoding="utf-8").readline())
    print(json.dumps(response, ensure_ascii=False))
    return 0 if response.get("ok") else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Agents System resident application runtime")
    sub = result.add_subparsers(dest="action", required=True)
    add = sub.add_parser("add")
    add.add_argument("-r", "--name", "--repo-name", dest="name", required=True)
    add.add_argument("--repository-path", "--repo-path")
    add.add_argument("--entrypoint")
    add.add_argument("--start", action="store_true")
    sub.add_parser("list")
    sub.add_parser("status")
    system_status_parser = sub.add_parser("system-status")
    system_status_parser.add_argument("--json", action="store_true")
    sub.add_parser("start")
    sub.add_parser("stop")
    remove = sub.add_parser("remove")
    remove.add_argument("--name", required=True)
    call = sub.add_parser("call")
    call.add_argument("--name", required=True)
    call.add_argument("--payload", default="{}")
    user_create = sub.add_parser("user-create")
    user_create.add_argument("-u", "--user", default="user-system")
    user_create.add_argument("--yes", action="store_true")
    user_get = sub.add_parser("user-get", add_help=False)
    user_get.add_argument("-u", "--user")
    user_get.add_argument("-h", "--home", action="store_true")
    user_get.add_argument("-n", "--name", action="store_true")
    user_get.add_argument("-g", "--group", action="store_true")
    sub.add_parser("user-list")
    user_set = sub.add_parser("user-set")
    user_set.add_argument("-u", "--user", required=True)
    user_set.add_argument("--yes", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.action == "add":
        return add_module(arguments)
    if arguments.action == "remove":
        return remove_module(arguments)
    if arguments.action == "list":
        print(json.dumps(read_registry(), ensure_ascii=False))
        return 0
    if arguments.action == "status":
        print(json.dumps(runtime_status(), ensure_ascii=False))
        return 0
    if arguments.action == "system-status":
        return print_system_status(system_status(), arguments.json)
    if arguments.action == "user-create":
        return create_user(arguments)
    if arguments.action == "user-get":
        return get_user(arguments)
    if arguments.action == "user-list":
        return list_users()
    if arguments.action == "user-set":
        return set_user(arguments)
    if arguments.action == "start":
        return start_runtime()
    if arguments.action == "stop":
        return stop_runtime()
    return call_module(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
