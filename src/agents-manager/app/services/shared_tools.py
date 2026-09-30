from __future__ import annotations

import shlex
import shutil
import tempfile

from dataclasses import dataclass
from pathlib import Path

from app.services.agent_config import BootstrapProcess
from app.services.process import ProcessRunner


@dataclass(frozen=True)
class SharedTool:
    """A repository script copied into one agent's private tools directory."""

    name: str
    source: Path
    destination: Path
    interpreter: str | None


class SharedToolsService:
    """Deploy shared scripts as snapshots and generate an idempotent launcher."""

    BOOTSTRAP_NAME = "bootstrap.sh"
    LEGACY_TOOL_NAMES = ("agents_wakeup", "message")

    def __init__(self, runner: ProcessRunner) -> None:
        self.runner = runner

    def deploy(
        self,
        *,
        source: Path,
        destination: Path,
        owner: str,
        bootstrap: tuple[BootstrapProcess, ...],
        replace_existing: bool,
        privileged: bool,
        dry_run: bool,
    ) -> None:
        tools = self._discover(source, destination)
        self._validate_bootstrap(bootstrap, tools)

        if dry_run:
            print(f"[DRY] create shared tools dir {destination}")
            for tool in tools:
                print(f"[DRY] copy {tool.source} -> {tool.destination}")
            print(f"[DRY] generate {destination / self.BOOTSTRAP_NAME}")
            return

        self._prepare_directory(destination, owner, privileged)
        if replace_existing:
            self._remove_legacy_tools(destination, privileged)
        for tool in tools:
            self._install_file(
                tool.source,
                tool.destination,
                owner=owner,
                privileged=privileged,
                replace_existing=replace_existing,
            )

        content = self.render_bootstrap(bootstrap, tools)
        self._install_content(
            content,
            destination / self.BOOTSTRAP_NAME,
            owner=owner,
            privileged=privileged,
            replace_existing=replace_existing,
        )

    def _remove_legacy_tools(self, destination: Path, privileged: bool) -> None:
        for name in self.LEGACY_TOOL_NAMES:
            legacy = destination / name
            if privileged:
                self.runner.run_privileged(["rm", "-f", str(legacy)])
            else:
                legacy.unlink(missing_ok=True)

    def start_bootstrap(
        self,
        *,
        destination: Path,
        owner: str,
        environment: dict[str, str],
        configured: bool,
        dry_run: bool,
    ) -> None:
        """Start configured background tools immediately as the agent user."""
        if not configured:
            return
        bootstrap = destination / self.BOOTSTRAP_NAME
        command = [
            "env",
            "AGENT_BOOTSTRAP_RESTART=1",
            *(f"{name}={value}" for name, value in sorted(environment.items())),
            "bash",
            str(bootstrap),
        ]
        if dry_run:
            print(
                f"[DRY] start agent bootstrap as {owner}: "
                f"{self.runner.printable(command)}"
            )
            return
        self.runner.run_as_user(owner, command)

    def _discover(self, source: Path, destination: Path) -> list[SharedTool]:
        if not source.is_dir():
            return []

        tools: list[SharedTool] = []
        for item in sorted(source.iterdir(), key=lambda path: path.name):
            if item.name.startswith("."):
                continue
            if item.name == self.BOOTSTRAP_NAME:
                raise RuntimeError(
                    f"Reserved shared tool name {self.BOOTSTRAP_NAME}: {item}"
                )
            try:
                resolved = item.resolve(strict=True)
            except (FileNotFoundError, RuntimeError) as exc:
                raise RuntimeError(f"Broken shared tool link: {item}") from exc
            if not resolved.is_file():
                raise RuntimeError(f"Shared tool must resolve to a file: {item}")

            suffix = resolved.suffix.lower()
            interpreter = "python3" if suffix == ".py" else None
            if suffix in {".sh", ".bash"}:
                interpreter = "bash"
            tools.append(
                SharedTool(
                    name=item.name,
                    source=resolved,
                    destination=destination / item.name,
                    interpreter=interpreter,
                )
            )
        return tools

    @staticmethod
    def _validate_bootstrap(
        bootstrap: tuple[BootstrapProcess, ...],
        tools: list[SharedTool],
    ) -> None:
        by_name = {tool.name: tool for tool in tools}
        by_stem: dict[str, list[SharedTool]] = {}
        for tool in tools:
            by_stem.setdefault(Path(tool.name).stem, []).append(tool)

        for process in bootstrap:
            if process.name in by_name:
                continue
            matches = by_stem.get(process.name, [])
            if len(matches) == 1:
                continue
            if len(matches) > 1:
                raise RuntimeError(
                    f"Bootstrap tool name is ambiguous: {process.name}"
                )
            raise RuntimeError(
                f"Bootstrap tool is not present in agents/shared/scripts: {process.name}"
            )

    @classmethod
    def render_bootstrap(
        cls,
        bootstrap: tuple[BootstrapProcess, ...],
        tools: list[SharedTool],
    ) -> str:
        by_name = {tool.name: tool for tool in tools}
        by_stem = {Path(tool.name).stem: tool for tool in tools}
        lines = [
            "#!/usr/bin/env bash",
            "set -uo pipefail",
            "",
            'state_dir="${AGENT_BOOTSTRAP_STATE_DIR:-${AGENT_HOME:-$HOME}/.bootstrap}"',
            'mkdir -p -- "$state_dir/logs" "$state_dir/pids"',
            'exec 9>"$state_dir/bootstrap.lock"',
            'command -v flock >/dev/null 2>&1 && flock 9',
            "",
            "process_matches_prefix() {",
            '    local pid="$1"',
            '    local count="$2"',
            "    shift 2",
            '    local -a expected=("$@")',
            "    local -a actual=()",
            "    local index",
            '    mapfile -d "" -t actual < "/proc/$pid/cmdline" 2>/dev/null || return 1',
            '    [[ "${#actual[@]}" -ge "$count" ]] || return 1',
            '    [[ "${#expected[@]}" -ge "$count" ]] || return 1',
            '    for ((index = 0; index < count; index++)); do',
            '        [[ "${actual[$index]}" == "${expected[$index]}" ]] || return 1',
            "    done",
            "}",
            "",
            "stop_processes() {",
            '    local -a pids=("$@")',
            "    local pid alive",
            '    ((${#pids[@]})) || return 0',
            '    kill "${pids[@]}" 2>/dev/null || true',
            '    for _ in {1..50}; do',
            "        alive=0",
            '        for pid in "${pids[@]}"; do',
            '            kill -0 "$pid" 2>/dev/null && alive=1',
            "        done",
            '        ((alive)) || return 0',
            "        sleep 0.1",
            "    done",
            '    for pid in "${pids[@]}"; do',
            '        kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true',
            "    done",
            "}",
            "",
            "start_background() {",
            '    local name="$1"',
            "    shift",
            '    local pid_file="$state_dir/pids/$name.pid"',
            '    local log_file="$state_dir/logs/$name.log"',
            "    local pid process_dir match_count=1",
            "    local -a matching=()",
            "",
            '    if [[ "${AGENT_BOOTSTRAP_RESTART:-0}" == "1" ]]; then',
            '        [[ "$1" == python3 || "$1" == bash ]] && match_count=2',
            '        for process_dir in /proc/[0-9]*; do',
            '            [[ -O "$process_dir" ]] || continue',
            '            pid="${process_dir##*/}"',
            '            process_matches_prefix "$pid" "$match_count" "$@" && matching+=("$pid")',
            "        done",
            '        stop_processes "${matching[@]}"',
            '    elif [[ -r "$pid_file" ]]; then',
            '        read -r pid < "$pid_file" || true',
            '        if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then',
            "            return 0",
            "        fi",
            "    fi",
            "",
            '    nohup "$@" 9>&- >>"$log_file" 2>&1 </dev/null &',
            '    printf "%s\\n" "$!" > "$pid_file"',
            "}",
        ]

        for process in bootstrap:
            tool = by_name.get(process.name) or by_stem[process.name]
            command = []
            if tool.interpreter is not None:
                command.append(tool.interpreter)
            command.append(str(tool.destination))
            for flag in process.flags:
                command.append(flag.flag)
                if flag.value is not None:
                    command.append(flag.value)
            rendered = " ".join(shlex.quote(value) for value in command)
            lines.extend([
                "",
                f"start_background {shlex.quote(process.name)} {rendered}",
            ])

        lines.append("")
        return "\n".join(lines)

    def _prepare_directory(
        self,
        destination: Path,
        owner: str,
        privileged: bool,
    ) -> None:
        if privileged:
            self.runner.run_privileged([
                "install", "-d", "-o", owner, "-g", owner, "-m", "0700",
                str(destination),
            ])
            return
        destination.mkdir(parents=True, exist_ok=True)
        destination.chmod(0o700)

    def _install_file(
        self,
        source: Path,
        destination: Path,
        *,
        owner: str,
        privileged: bool,
        replace_existing: bool,
    ) -> None:
        self._prepare_target(destination, privileged, replace_existing)
        if privileged:
            self.runner.run_privileged([
                "install", "-o", owner, "-g", owner, "-m", "0750",
                str(source), str(destination),
            ])
            return
        shutil.copy2(source, destination)
        destination.chmod(0o750)

    def _install_content(
        self,
        content: str,
        destination: Path,
        *,
        owner: str,
        privileged: bool,
        replace_existing: bool,
    ) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False
        ) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        try:
            self._install_file(
                temporary,
                destination,
                owner=owner,
                privileged=privileged,
                replace_existing=replace_existing,
            )
        finally:
            temporary.unlink(missing_ok=True)

    def _prepare_target(
        self,
        target: Path,
        privileged: bool,
        replace_existing: bool,
    ) -> None:
        if not (target.exists() or target.is_symlink()):
            return
        if not replace_existing:
            raise FileExistsError(f"{target} already exists; use --force.")
        if target.is_dir() and not target.is_symlink():
            raise RuntimeError(f"Managed tool target is a directory: {target}")
        if privileged:
            self.runner.run_privileged(["rm", "-f", "--", str(target)])
        else:
            target.unlink()
