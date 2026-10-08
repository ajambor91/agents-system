"""Root-owned append-in-order installation journal."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import InstallationError


class InstallJournal:
    """Persist mutation intent before destructive replacement and final state after it."""

    def __init__(self, root: Path, state: dict[str, Any]) -> None:
        self.root = root
        self.path = root / "journal.json"
        self.backups = root / "backups"
        self.state = state

    @classmethod
    def create(cls, app_name: str, configuration: dict[str, Any]) -> "InstallJournal":
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        prefix = f"{app_name}-install_{timestamp}_{secrets.token_hex(4)}_"
        root = Path(tempfile.mkdtemp(prefix=prefix, dir="/tmp"))
        root.chmod(0o700)
        journal = cls(root, {
            "schema_version": 1,
            "kind": "agents-system-install-journal",
            "operation_id": root.name,
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "configuration": configuration,
            "mutations": [],
            "outputs": {},
        })
        journal.backups.mkdir(mode=0o700)
        journal._write()
        return journal

    @classmethod
    def open(cls, root: Path) -> "InstallJournal":
        root = root.expanduser()
        if (
            not root.is_absolute()
            or root.parent != Path("/tmp")
            or root.is_symlink()
            or not root.is_dir()
            or not re.fullmatch(
                r"[a-z][a-z0-9-]*-install_\d{8}T\d{6}Z_[a-f0-9]+_[A-Za-z0-9_-]+",
                root.name,
            )
        ):
            raise InstallationError(f"Nieprawidłowy katalog dziennika: {root}")
        current = Path(root.anchor)
        for component in root.parts[1:]:
            current /= component
            if current.is_symlink():
                raise InstallationError(f"Komponent dziennika jest dowiązaniem: {current}")
        metadata = root.stat()
        if metadata.st_uid != 0 or metadata.st_mode & 0o777 != 0o700:
            raise InstallationError("Dziennik musi należeć do root i mieć tryb 0700")
        try:
            state = json.loads((root / "journal.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InstallationError(f"Nie można odczytać dziennika {root}: {exc}") from exc
        if (
            not isinstance(state, dict)
            or state.get("kind") != "agents-system-install-journal"
            or state.get("operation_id") != root.name
        ):
            raise InstallationError("Dziennik ma nieprawidłową tożsamość")
        return cls(root, state)

    def record(self, kind: str, **details: Any) -> int:
        mutation = {"kind": kind, "state": "applied", **details}
        self.state["mutations"].append(mutation)
        self._write()
        return len(self.state["mutations"]) - 1

    def prepare(self, kind: str, **details: Any) -> int:
        mutation = {"kind": kind, "state": "prepared", **details}
        self.state["mutations"].append(mutation)
        self._write()
        return len(self.state["mutations"]) - 1

    def applied(self, index: int) -> None:
        self.state["mutations"][index]["state"] = "applied"
        self._write()

    def backup(self, path: Path) -> tuple[str, dict[str, Any]]:
        if not path.exists() and not path.is_symlink():
            raise InstallationError(f"Nie można wykonać kopii nieistniejącej ścieżki: {path}")
        entries = [path, *path.rglob("*")] if path.is_dir() and not path.is_symlink() else [path]
        tree: list[dict[str, Any]] = []
        for entry in entries:
            entry_stat = entry.lstat()
            tree.append({
                "path": "." if entry == path else str(entry.relative_to(path)),
                "mode": entry_stat.st_mode & 0o7777,
                "uid": entry_stat.st_uid,
                "gid": entry_stat.st_gid,
                "symlink": entry.is_symlink(),
            })
        metadata: dict[str, Any] = {"tree": tree}
        destination = self.backups / f"{len(self.state['mutations']):04d}-{secrets.token_hex(4)}"
        if path.is_symlink():
            destination.symlink_to(os.readlink(path))
        elif path.is_dir():
            shutil.copytree(path, destination, symlinks=True)
        else:
            shutil.copy2(path, destination, follow_symlinks=False)
        return str(destination.relative_to(self.root)), metadata

    def finish(self, status: str, *, outputs: dict[str, Any] | None = None, error: str | None = None) -> None:
        self.state["status"] = status
        self.state["finished_at"] = datetime.now(timezone.utc).isoformat()
        if outputs is not None:
            self.state["outputs"] = outputs
        if error is not None:
            self.state["error"] = error
        self._write()

    def _write(self) -> None:
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(4)}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(self.state, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, self.path)
        except OSError as exc:
            raise InstallationError(f"Nie można zapisać dziennika {self.path}: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)
