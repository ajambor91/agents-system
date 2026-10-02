from __future__ import annotations

import json
import re

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_catalog import AgentCatalog


@dataclass(frozen=True)
class AgentExecutionConfig:
    """Host-command execution policy selected by one agent definition."""

    backend: str
    required: bool
    timeout_seconds: int

    def to_document(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "required": self.required,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class AgentToolPolicy:
    """Validated OpenClaw tool visibility policy."""

    profile: str | None
    allow: tuple[str, ...]
    also_allow: tuple[str, ...]
    deny: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {}
        if self.profile is not None:
            document["profile"] = self.profile
        if self.allow:
            document["allow"] = list(self.allow)
        if self.also_allow:
            document["also_allow"] = list(self.also_allow)
        if self.deny:
            document["deny"] = list(self.deny)
        return document

    def to_openclaw_document(self) -> dict[str, Any]:
        document = self.to_document()
        if "also_allow" in document:
            document["alsoAllow"] = document.pop("also_allow")
        return document


@dataclass(frozen=True)
class BootstrapFlag:
    """One argv item pair passed to a managed background tool."""

    flag: str
    value: str | None

    def to_document(self) -> dict[str, str]:
        document = {"flag": self.flag}
        if self.value is not None:
            document["value"] = self.value
        return document


@dataclass(frozen=True)
class BootstrapProcess:
    """A shared tool that should be kept running for an agent."""

    name: str
    flags: tuple[BootstrapFlag, ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "flags": [flag.to_document() for flag in self.flags],
        }


@dataclass(frozen=True)
class AgentConfig:
    """Validated, versioned defaults for one agent definition."""

    name: str
    user: str | None
    model: str | None
    default: bool
    gateway_host: str | None
    gateway_port: int | None
    execution: AgentExecutionConfig | None
    tools: AgentToolPolicy | None
    bootstrap: tuple[BootstrapProcess, ...]
    source: Path | None

    def effective_document(
        self,
        *,
        linux_user: str,
        model: str | None,
        gateway_user: str,
        workspace: Path,
    ) -> dict[str, Any]:
        """Return the read-only configuration exposed inside the workspace."""
        document = {
            "schema_version": 1,
            "name": self.name,
            "user": linux_user,
            "model": model,
            "default": self.default,
            "gateway_host": self.gateway_host,
            "gateway_port": self.gateway_port,
            "gateway_user": gateway_user,
            "workspace": str(workspace),
        }
        if self.execution is not None:
            document["execution"] = self.execution.to_document()
        if self.tools is not None:
            document["tools"] = self.tools.to_document()
        if self.bootstrap:
            document["bootstrap"] = [
                process.to_document()
                for process in self.bootstrap
            ]
        return document

    def openclaw_tools_document(self) -> dict[str, Any] | None:
        """Return the authored policy in OpenClaw's camelCase schema."""
        if self.tools is None:
            return None
        return self.tools.to_openclaw_document()


class AgentConfigService:
    """Load definition defaults without letting repository JSON bypass validation."""

    ALLOWED_FIELDS = frozenset({
        "name",
        "user",
        "model",
        "default",
        "gateway_host",
        "gateway_port",
        "execution",
        "tools",
        "bootstrap",
    })
    TOOL_PROFILES = frozenset({"minimal", "coding", "messaging", "full"})
    EXECUTION_BACKENDS = frozenset({"agent-executor"})
    TOOL_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    FLAG_PATTERN = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9_-]*$")

    def __init__(self, catalog: AgentCatalog) -> None:
        self.catalog = catalog

    def resolve(self, name: str | None) -> AgentConfig:
        """Resolve an explicit definition or the single default definition."""
        if name is not None:
            return self.load(name)

        defaults = [
            config
            for agent_name in self.catalog.list_agents()
            if (config := self.load(agent_name)).default
        ]
        if not defaults:
            raise RuntimeError(
                "No default agent is configured; use --name or set exactly one "
                "agents/<name>/config.json field default=true."
            )
        if len(defaults) > 1:
            names = ", ".join(config.name for config in defaults)
            raise RuntimeError(
                f"More than one default agent is configured: {names}."
            )
        return defaults[0]

    def load(self, name: str) -> AgentConfig:
        agent_root = self.catalog.get_agent_root(name)
        config_path = agent_root / "config.json"
        if not config_path.is_file():
            return AgentConfig(
                name=name,
                user=None,
                model=None,
                default=False,
                gateway_host=None,
                gateway_port=None,
                execution=None,
                tools=None,
                bootstrap=(),
                source=None,
            )

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Invalid agent config {config_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"Agent config must be a JSON object: {config_path}")

        unknown = sorted(set(data) - self.ALLOWED_FIELDS)
        if unknown:
            raise RuntimeError(
                f"Unknown agent config fields in {config_path}: {', '.join(unknown)}"
            )

        configured_name = data.get("name", name)
        if not isinstance(configured_name, str) or configured_name != name:
            raise RuntimeError(
                f"Agent config name must match its directory '{name}': {config_path}"
            )

        user = self._optional_string(data, "user", config_path)
        model = self._optional_string(data, "model", config_path)
        gateway_host = self._optional_string(data, "gateway_host", config_path)

        default = data.get("default", False)
        if not isinstance(default, bool):
            raise RuntimeError(f"Agent config default must be boolean: {config_path}")

        gateway_port = data.get("gateway_port")
        if gateway_port is not None and (
            isinstance(gateway_port, bool)
            or not isinstance(gateway_port, int)
            or not 1 <= gateway_port <= 65535
        ):
            raise RuntimeError(
                f"Agent config gateway_port must be in range 1..65535: {config_path}"
            )

        execution = self._execution(data.get("execution"), config_path)
        tools = self._tools(data.get("tools"), config_path)
        bootstrap = self._bootstrap(data.get("bootstrap"), config_path)
        if execution is not None and execution.required:
            if tools is None:
                raise RuntimeError(
                    f"Agent config with required execution needs tools policy: {config_path}"
                )
            visible = set(tools.allow) | set(tools.also_allow)
            if "agent_exec" not in visible:
                raise RuntimeError(
                    f"Required agent-executor must expose agent_exec: {config_path}"
                )
            missing_denies = {"exec", "process"} - set(tools.deny)
            if missing_denies:
                raise RuntimeError(
                    "Required agent-executor must deny native tools "
                    f"{', '.join(sorted(missing_denies))}: {config_path}"
                )

        return AgentConfig(
            name=name,
            user=user,
            model=model,
            default=default,
            gateway_host=gateway_host,
            gateway_port=gateway_port,
            execution=execution,
            tools=tools,
            bootstrap=bootstrap,
            source=config_path,
        )

    def _execution(
        self,
        value: Any,
        path: Path,
    ) -> AgentExecutionConfig | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise RuntimeError(f"Agent config execution must be an object: {path}")
        unknown = sorted(set(value) - {"backend", "required", "timeout_seconds"})
        if unknown:
            raise RuntimeError(
                f"Unknown execution fields in {path}: {', '.join(unknown)}"
            )
        backend = value.get("backend")
        if backend not in self.EXECUTION_BACKENDS:
            raise RuntimeError(
                f"Unsupported execution backend in {path}: {backend}"
            )
        required = value.get("required", True)
        if not isinstance(required, bool):
            raise RuntimeError(f"Agent config execution.required must be boolean: {path}")
        timeout = value.get("timeout_seconds", 300)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 3600:
            raise RuntimeError(
                f"Agent config execution.timeout_seconds must be in range 1..3600: {path}"
            )
        return AgentExecutionConfig(backend, required, timeout)

    def _tools(self, value: Any, path: Path) -> AgentToolPolicy | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise RuntimeError(f"Agent config tools must be an object: {path}")
        unknown = sorted(set(value) - {"profile", "allow", "also_allow", "deny"})
        if unknown:
            raise RuntimeError(f"Unknown tools fields in {path}: {', '.join(unknown)}")
        profile = value.get("profile")
        if profile is not None and profile not in self.TOOL_PROFILES:
            raise RuntimeError(f"Unsupported tools profile in {path}: {profile}")
        return AgentToolPolicy(
            profile=profile,
            allow=self._tool_names(value.get("allow"), "allow", path),
            also_allow=self._tool_names(value.get("also_allow"), "also_allow", path),
            deny=self._tool_names(value.get("deny"), "deny", path),
        )

    def _bootstrap(
        self,
        value: Any,
        path: Path,
    ) -> tuple[BootstrapProcess, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise RuntimeError(f"Agent config bootstrap must be an array: {path}")

        processes: list[BootstrapProcess] = []
        for index, item in enumerate(value):
            label = f"bootstrap[{index}]"
            if not isinstance(item, dict):
                raise RuntimeError(f"Agent config {label} must be an object: {path}")
            unknown = sorted(set(item) - {"name", "flags"})
            if unknown:
                raise RuntimeError(
                    f"Unknown {label} fields in {path}: {', '.join(unknown)}"
                )
            name = item.get("name")
            if (
                not isinstance(name, str)
                or not name.strip()
                or Path(name).name != name
                or self.TOOL_FILENAME_PATTERN.fullmatch(name) is None
            ):
                raise RuntimeError(
                    f"Agent config {label}.name must be a tool filename: {path}"
                )

            raw_flags = item.get("flags", [])
            if not isinstance(raw_flags, list):
                raise RuntimeError(
                    f"Agent config {label}.flags must be an array: {path}"
                )
            flags: list[BootstrapFlag] = []
            for flag_index, raw_flag in enumerate(raw_flags):
                flag_label = f"{label}.flags[{flag_index}]"
                if not isinstance(raw_flag, dict):
                    raise RuntimeError(
                        f"Agent config {flag_label} must be an object: {path}"
                    )
                unknown_flag = sorted(set(raw_flag) - {"flag", "value"})
                if unknown_flag:
                    raise RuntimeError(
                        f"Unknown {flag_label} fields in {path}: "
                        f"{', '.join(unknown_flag)}"
                    )
                flag = raw_flag.get("flag")
                if (
                    not isinstance(flag, str)
                    or self.FLAG_PATTERN.fullmatch(flag) is None
                ):
                    raise RuntimeError(
                        f"Agent config {flag_label}.flag must start with '-': {path}"
                    )
                raw_value = raw_flag.get("value")
                if raw_value is not None and (
                    isinstance(raw_value, bool)
                    or not isinstance(raw_value, (str, int, float))
                ):
                    raise RuntimeError(
                        f"Agent config {flag_label}.value must be scalar: {path}"
                    )
                if isinstance(raw_value, str) and any(
                    character in raw_value for character in ("\x00", "\n", "\r")
                ):
                    raise RuntimeError(
                        f"Agent config {flag_label}.value contains a control "
                        f"character: {path}"
                    )
                flags.append(
                    BootstrapFlag(
                        flag=flag,
                        value=None if raw_value is None else str(raw_value),
                    )
                )
            processes.append(BootstrapProcess(name=name, flags=tuple(flags)))

        names = [process.name for process in processes]
        if len(names) != len(set(names)):
            raise RuntimeError(f"Agent config bootstrap contains duplicates: {path}")
        return tuple(processes)

    @staticmethod
    def _tool_names(value: Any, field: str, path: Path) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise RuntimeError(
                f"Agent config tools.{field} must be a string array: {path}"
            )
        names = tuple(item.strip() for item in value)
        if len(set(names)) != len(names):
            raise RuntimeError(f"Agent config tools.{field} contains duplicates: {path}")
        return names

    @staticmethod
    def _optional_string(
        data: dict[str, Any],
        field: str,
        path: Path,
    ) -> str | None:
        value = data.get(field)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"Agent config {field} must be a non-empty string: {path}"
            )
        return value
