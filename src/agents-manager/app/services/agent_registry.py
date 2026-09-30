"""Persistent agent inventory synchronized with runtime state and OpenClaw."""

from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.context import ApplicationContext
from app.services.openclaw import OpenClawService
from app.services.state import AgentStateService


class AgentRegistryService:
    """Build and atomically persist the current cross-system agent snapshot."""

    SCHEMA_VERSION = 1
    RECENT_TASK_LIMIT = 20

    def __init__(
        self,
        context: ApplicationContext,
        state: AgentStateService,
        openclaw: OpenClawService,
    ) -> None:
        self.context = context
        self.state = state
        self.openclaw = openclaw
        self.path = context.state_root / "agents.json"

    def sync(
        self,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Merge retained records, runtime files, task history and OpenClaw."""
        previous = self.read()
        previous_agents = previous.get("agents", {})
        runtimes = self._runtime_records()

        openclaw_error: str | None = None
        try:
            openclaw_agents = {
                str(item["id"]): item
                for item in self.openclaw.list_agents()
                if item.get("id")
            }
        except Exception as exc:
            openclaw_agents = {}
            openclaw_error = str(exc)

        names = sorted(
            set(previous_agents)
            | set(runtimes)
            | set(openclaw_agents)
        )
        timestamp = self._timestamp()
        agents: dict[str, dict[str, Any]] = {}

        for name in names:
            prior = previous_agents.get(name, {})
            runtime = runtimes.get(name)
            openclaw_record = openclaw_agents.get(name)
            managed = bool(runtime) or bool(prior.get("managed"))
            openclaw_status = self._openclaw_status(
                openclaw_record,
                prior.get("openclaw", {}),
                openclaw_error,
            )
            tasks = self._tasks(
                runtime,
                prior.get("tasks", {}),
            )
            agents[name] = self._record(
                name=name,
                prior=prior,
                runtime=runtime,
                openclaw_record=openclaw_record,
                openclaw_status=openclaw_status,
                tasks=tasks,
                managed=managed,
                timestamp=timestamp,
            )

        document: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "updated_at": timestamp,
            "agents": agents,
        }

        if dry_run:
            print(f"[DRY] write {self.path}")
            return document

        self.state.prepare_root()
        self.state.write_json(
            self.path,
            document,
            mode="0640",
        )
        return document

    def read(self) -> dict[str, Any]:
        """Read the retained registry, rejecting corruption before overwrite."""
        if not self.path.is_file():
            return {
                "schema_version": self.SCHEMA_VERSION,
                "agents": {},
            }
        try:
            value = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Invalid agent registry {self.path}: {exc}"
            ) from exc
        if not isinstance(value, dict) or not isinstance(value.get("agents"), dict):
            raise RuntimeError(
                f"Invalid agent registry structure: {self.path}"
            )
        return value

    @staticmethod
    def get(
        document: dict[str, Any],
        name: str,
    ) -> dict[str, Any]:
        """Return one named record from a synchronized document."""
        agents = document.get("agents", {})
        if name not in agents:
            raise RuntimeError(f"Agent is not registered: {name}")
        return agents[name]

    def _runtime_records(self) -> dict[str, dict[str, Any]]:
        if not self.context.state_root.is_dir():
            return {}
        records: dict[str, dict[str, Any]] = {}
        try:
            directories = list(self.context.state_root.iterdir())
        except OSError as exc:
            raise RuntimeError(
                f"Cannot list agent state: {self.context.state_root}"
            ) from exc
        for directory in directories:
            if not directory.is_dir():
                continue
            runtime_path = directory / "runtime.json"
            if not runtime_path.is_file():
                continue
            try:
                value = json.loads(
                    runtime_path.read_text(encoding="utf-8")
                )
                if not isinstance(value, dict):
                    raise ValueError("runtime must be an object")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                value = {
                    "agent": directory.name,
                    "runtime_error": str(exc),
                }
            name = str(value.get("agent") or directory.name)
            records[name] = value
        return records

    def _openclaw_status(
        self,
        current: dict[str, Any] | None,
        previous: dict[str, Any],
        error: str | None,
    ) -> dict[str, Any]:
        if error:
            result = dict(previous)
            result.update({
                "status": "unavailable",
                "connected": False,
                "error": error,
            })
            return result
        if current is None:
            result = dict(previous)
            result.update({
                "status": "deleted",
                "connected": False,
            })
            result.pop("error", None)
            return result
        result = {
            "status": "connected",
            "connected": True,
        }
        for key in (
            "id",
            "name",
            "identityName",
            "identityEmoji",
            "workspace",
            "agentDir",
            "model",
            "bindings",
            "isDefault",
            "createdVia",
            "createdAt",
        ):
            if key in current:
                result[key] = current[key]
        return result

    def _record(
        self,
        *,
        name: str,
        prior: dict[str, Any],
        runtime: dict[str, Any] | None,
        openclaw_record: dict[str, Any] | None,
        openclaw_status: dict[str, Any],
        tasks: dict[str, Any],
        managed: bool,
        timestamp: str,
    ) -> dict[str, Any]:
        runtime = runtime or {}
        openclaw_state = str(openclaw_status["status"])
        if managed and runtime:
            status = (
                "active"
                if openclaw_state == "connected"
                else "disconnected"
                if openclaw_state == "deleted"
                else "unknown"
            )
        elif managed:
            status = (
                "deleted"
                if openclaw_state == "deleted"
                else "degraded"
            )
        else:
            status = (
                "external"
                if openclaw_state == "connected"
                else "deleted"
                if openclaw_state == "deleted"
                else "unknown"
            )

        display_name = (
            (openclaw_record or {}).get("identityName")
            or (openclaw_record or {}).get("name")
            or prior.get("name")
            or name
        )
        record: dict[str, Any] = {
            "id": name,
            "name": display_name,
            "managed": managed,
            "status": status,
            "linux_user": runtime.get("linux_user", prior.get("linux_user")),
            "gateway_user": runtime.get("gateway_user", prior.get("gateway_user")),
            "home": runtime.get("home", prior.get("home")),
            "workspace": runtime.get(
                "workspace",
                (openclaw_record or {}).get("workspace", prior.get("workspace")),
            ),
            "state_dir": str(self.context.state_root / name) if managed else None,
            "runtime": {
                "status": "available" if runtime else "missing",
                "path": str(self.context.state_root / name / "runtime.json") if managed else None,
            },
            "openclaw": openclaw_status,
            "tasks": tasks,
            "installed_at": prior.get("installed_at") or (timestamp if runtime else None),
            "updated_at": timestamp,
        }
        if runtime.get("runtime_error"):
            record["runtime"]["status"] = "error"
            record["runtime"]["error"] = runtime["runtime_error"]
            record["status"] = "unknown"
        return record

    def _tasks(
        self,
        runtime: dict[str, Any] | None,
        previous: dict[str, Any],
    ) -> dict[str, Any]:
        if not runtime or not runtime.get("home"):
            return previous or self._empty_tasks()
        history_path = (
            Path(str(runtime["home"]))
            / ".history"
            / "history.json"
        )
        if not history_path.is_file():
            return self._empty_tasks()
        try:
            lines = history_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            result = dict(previous or self._empty_tasks())
            result["status"] = "unavailable"
            result["error"] = str(exc)
            return result

        started: dict[str, dict[str, Any]] = {}
        completed: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            execution_id = str(event.get("execution_id") or "")
            if not execution_id:
                continue
            if event.get("event") == "command_started":
                started[execution_id] = {
                    "execution_id": execution_id,
                    "command": event.get("command"),
                    "requested_by": event.get("requested_by"),
                    "started_at": event.get("timestamp"),
                    "status": "running",
                }
            elif event.get("event") == "command_completed":
                task = started.pop(execution_id, {
                    "execution_id": execution_id,
                    "command": event.get("command"),
                    "requested_by": event.get("requested_by"),
                })
                try:
                    return_code = int(event.get("return_code", 1))
                except (TypeError, ValueError):
                    return_code = 1
                task.update({
                    "completed_at": event.get("timestamp"),
                    "return_code": return_code,
                    "status": "completed" if return_code == 0 else "failed",
                })
                completed.append(task)

        active = list(started.values())
        recent = list(reversed(completed[-self.RECENT_TASK_LIMIT:]))
        failed = sum(1 for task in completed if task["status"] == "failed")
        task_status = (
            "running"
            if active
            else recent[0]["status"]
            if recent and recent[0]["status"] == "failed"
            else "idle"
        )
        return {
            "status": task_status,
            "total": len(completed) + len(active),
            "running": len(active),
            "completed": len(completed) - failed,
            "failed": failed,
            "active": active,
            "recent": recent,
            "history_path": str(history_path),
        }

    @staticmethod
    def _empty_tasks() -> dict[str, Any]:
        return {
            "status": "idle",
            "total": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "active": [],
            "recent": [],
        }

    @staticmethod
    def _timestamp() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
