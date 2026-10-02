"""Journal-driven reversal of an Agents System installation."""

from __future__ import annotations

import argparse
import grp
import os
import pwd
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from .errors import InstallationError
from .journal import InstallJournal


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


class InstallationRollback:
    """Reverse only mutations explicitly proven by a validated journal."""

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        effective_uid: int | None = None,
    ) -> None:
        self.runner = runner
        self.effective_uid = os.geteuid() if effective_uid is None else effective_uid

    def execute(self, journal_path: Path) -> dict[str, Any]:
        if self.effective_uid != 0:
            raise InstallationError("Rollback wymaga uprawnień root")
        journal = InstallJournal.open(journal_path)
        if journal.state.get("status") == "rolled-back":
            return {"journal": str(journal.root), "status": "already-rolled-back"}
        failures: list[str] = []
        for mutation in reversed(journal.state.get("mutations", [])):
            if mutation.get("state") not in {"prepared", "applied"}:
                continue
            try:
                self._reverse(journal, mutation)
                mutation["state"] = "reverted"
                journal._write()
            except Exception as exc:  # retain journal and continue reversing independent actions
                failures.append(f"{mutation.get('kind')}: {exc}")
        if failures:
            journal.finish("rollback-failed", error="; ".join(failures))
            raise InstallationError(
                f"Rollback niepełny; zachowano dziennik {journal.root}: {'; '.join(failures)}"
            )
        journal.finish("rolled-back")
        return {"journal": str(journal.root), "status": "rolled-back"}

    def _reverse(self, journal: InstallJournal, mutation: dict[str, Any]) -> None:
        kind = mutation["kind"]
        if kind == "created_path":
            _remove_path(self._validated_path(journal, mutation["path"]))
        elif kind == "replaced_path":
            target = self._validated_path(journal, mutation["path"])
            backup = (journal.root / mutation["backup"]).resolve(strict=False)
            try:
                backup.relative_to(journal.backups.resolve())
            except ValueError as exc:
                raise InstallationError("Kopia zapasowa wychodzi poza katalog dziennika") from exc
            if not backup.exists() and not backup.is_symlink():
                raise InstallationError(f"Brak kopii zapasowej: {backup}")
            _remove_path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.is_symlink():
                target.symlink_to(os.readlink(backup))
            elif backup.is_dir():
                shutil.copytree(backup, target, symlinks=True)
            else:
                shutil.copy2(backup, target, follow_symlinks=False)
            metadata = mutation.get("metadata", {})
            entries = metadata.get("tree") if isinstance(metadata, dict) else None
            if not isinstance(entries, list):
                entries = [{"path": ".", **metadata}]
            for entry in reversed(entries):
                relative = Path(str(entry.get("path", ".")))
                if relative.is_absolute() or ".." in relative.parts:
                    raise InstallationError("Niebezpieczna ścieżka metadanych kopii")
                restored = target if str(relative) == "." else target / relative
                if restored.is_symlink():
                    os.lchown(restored, int(entry.get("uid", 0)), int(entry.get("gid", 0)))
                elif restored.exists():
                    os.chmod(restored, int(entry.get("mode", 0o640)))
                    os.chown(restored, int(entry.get("uid", 0)), int(entry.get("gid", 0)))
        elif kind == "added_membership":
            self._run(["gpasswd", "-d", mutation["user"], mutation["group"]])
        elif kind == "created_user":
            try:
                pwd.getpwnam(mutation["name"])
            except KeyError:
                return
            self._run(["userdel", mutation["name"]])
        elif kind == "created_group":
            try:
                grp.getgrnam(mutation["name"])
            except KeyError:
                return
            self._run(["groupdel", mutation["name"]])
        elif kind == "service_enabled":
            self._run(["systemctl", "disable", "--now", mutation["unit"]])
        elif kind == "service_state":
            self._run(["systemctl", "daemon-reload"])
            if mutation.get("enabled"):
                self._run(["systemctl", "enable", mutation["unit"]])
            if mutation.get("active"):
                self._run(["systemctl", "start", mutation["unit"]])
        elif kind == "daemon_reload":
            self._run(["systemctl", "daemon-reload"])
        else:
            raise InstallationError(f"Nieznany typ mutacji w dzienniku: {kind}")

    @staticmethod
    def _validated_path(journal: InstallJournal, raw_path: str) -> Path:
        configuration = journal.state.get("configuration", {})
        path = Path(raw_path)
        if not path.is_absolute() or ".." in path.parts:
            raise InstallationError(f"Niebezpieczna ścieżka w dzienniku: {raw_path}")
        allowed_exact = {
            Path(configuration[name])
            for name in ("install_dir", "config_dir", "data_dir", "runtime_dir", "unit_path", "installed_modules_dir", "installed_modules_file")
            if isinstance(configuration.get(name), str)
        }
        installed_dir = configuration.get("installed_modules_dir")
        for parent in configuration.get("installed_modules_created_parents", []):
            if isinstance(installed_dir, str) and isinstance(parent, str):
                candidate = Path(parent)
                if candidate in Path(installed_dir).parents and candidate != Path(candidate.anchor):
                    allowed_exact.add(candidate)
        commands_dir = configuration.get("commands_dir")
        generated_environment_paths = {
            (Path(configuration[name]) / "src" / ".env").resolve(strict=False)
            for name in ("install_dir", "package_dir")
            if isinstance(configuration.get(name), str)
        }
        if path in allowed_exact or path.resolve(strict=False) in generated_environment_paths:
            return path
        if isinstance(commands_dir, str) and path.parent == Path(commands_dir):
            return path
        raise InstallationError(f"Ścieżka nie należy do instalacji: {path}")

    def _run(self, arguments: list[str]) -> None:
        completed = self.runner(arguments, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise InstallationError(completed.stderr.strip() or f"Polecenie nie powiodło się: {arguments[0]}")


def rollback_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rollback")
    parser.add_argument("--journal", required=True)
    return parser
