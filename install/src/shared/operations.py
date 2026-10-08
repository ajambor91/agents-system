"""Generic filesystem and process operations shared by lifecycle use-cases."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from typing import Any, Callable, TYPE_CHECKING

from ..errors import InstallationError
from .shared import remove

if TYPE_CHECKING:
    from ..journal import InstallJournal


def run_command(runner: Callable[..., subprocess.CompletedProcess[str]], arguments: list[str], *, allowed: set[int] | None = None, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    options = {"check": False, "capture_output": True, "text": True}
    if environment is not None:
        options["env"] = environment
    completed = runner(arguments, **options)
    if completed.returncode not in (allowed or {0}):
        raise InstallationError(completed.stderr.strip() or completed.stdout.strip() or f"Polecenie nie powiodło się: {arguments[0]}")
    return completed


def prepare_path_change(path: Path, journal: InstallJournal) -> int:
    if path.exists() or path.is_symlink():
        backup, metadata = journal.backup(path)
        return journal.prepare("replaced_path", path=str(path), backup=backup, metadata=metadata)
    return journal.prepare("created_path", path=str(path))


def replace_path(path: Path, journal: InstallJournal, writer: Callable[[], None]) -> None:
    index = prepare_path_change(path, journal)
    remove(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer()
    journal.applied(index)


def delete_path(path: Path, journal: InstallJournal) -> None:
    if path.exists() or path.is_symlink():
        index = prepare_path_change(path, journal)
        remove(path)
        journal.applied(index)


def atomic_copy(source: Path, target: Path, *, mode: int | None = None) -> None:
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    try:
        shutil.copy2(source, temporary)
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_link(source: Path, target: Path) -> None:
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    try:
        temporary.symlink_to(source)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(target: Path, document: dict[str, Any], *, mode: int = 0o640) -> None:
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_text(target: Path, content: str, *, mode: int = 0o640, owner: tuple[int, int] | None = None) -> None:
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        if owner is not None:
            os.chown(temporary, *owner)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def copy_payload_tree(source: Path, target: Path, *, application_sources: Path) -> None:
    """Copy source payload without a generated copy of the installer package."""
    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored = [name for name in names if name == '__pycache__']
        if Path(directory) == application_sources and 'install' in names:
            ignored.append('install')
        return ignored
    shutil.copytree(source, target, symlinks=True, ignore=ignore)
