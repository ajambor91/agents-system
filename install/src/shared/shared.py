"""The installation use-case defined by install/src/resources/installer.json."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Mapping, Sequence

from ..errors import InstallationError
from ..consts import  (

    REQUIRED_DEFAULTS, 
)
from ..context import get_mode
from ..enums import InstallerMode
def install_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="install", add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Potwierdza wykonanie operacji")
    parser.add_argument("-m", "--mode", choices=("system", "dev"), default="system")
    parser.add_argument("--system-user")
    parser.add_argument("--system-group")
    parser.add_argument("--target", "--install-dir", dest="target")
    parser.add_argument("--config-root", "--config-dir", dest="config_root")
    parser.add_argument("--data-dir")
    parser.add_argument("--runtime-dir")
    parser.add_argument("--bash-source", choices=("true", "false"))
    parser.add_argument("--commands-dir")
    parser.add_argument("--clone-repo", action="store_true")
    parser.add_argument("--user-system")
    parser.add_argument("--user-group")
    parser.add_argument("-i", "--invoker")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def lifecycle_parser(mode: InstallerMode) -> argparse.ArgumentParser:
    if mode == InstallerMode.INSTALL:
        return install_parser()
    parser = argparse.ArgumentParser(prog=mode.value, add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Potwierdza wykonanie operacji")
    parser.add_argument("--journal", required=True, help="Exact successful installation journal directory")
    if mode == InstallerMode.RECONFIGURE:
        parser.add_argument("--envs", required=True, help="Absolute path to a complete rendered app_env.json")
    if mode == InstallerMode.REINSTALL:
        parser.add_argument("--source", help="Absolute path to the replacement source checkout")
    if mode == InstallerMode.UNINSTALL:
        parser.add_argument("--purge-data", action="store_true", help="Also remove this installation's marked data directory")
    if mode != InstallerMode.ROLLBACK:
        parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def installer_parser(argv: Sequence[str], mode: InstallerMode | None = None) -> argparse.Namespace:
    return lifecycle_parser(mode or get_mode()).parse_args(argv)


def load_defaults(path: Path) -> dict[str, str | None]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallationError(f"Brak pliku wartości domyślnych: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallationError(f"Nie można odczytać {path}: {exc}") from exc
    if not isinstance(document, list):
        raise InstallationError("default_install.json musi być tablicą name/value")
    result: dict[str, str | None] = {}
    for offset, item in enumerate(document):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise InstallationError(f"default_install.json[{offset}] musi być obiektem name/value")
        name, value = item["name"], item.get("value")
        if name in result or (value is not None and (not isinstance(value, str) or not value)):
            raise InstallationError(f"Nieprawidłowa lub powtórzona wartość domyślna: {name}")
        result[name] = value
    missing = sorted(REQUIRED_DEFAULTS - result.keys())
    if missing:
        raise InstallationError("Brak wartości domyślnych: " + ", ".join(missing))
    return result


def absolute(value: str, name: str, *, must_exist: bool = False, preserve_symlinks: bool = False) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise InstallationError(f"{name} musi być bezpieczną ścieżką absolutną")
    resolved = path.absolute() if preserve_symlinks else path.resolve(strict=False)
    if must_exist and not resolved.is_dir():
        raise InstallationError(f"{name} nie jest istniejącym katalogiem: {resolved}")
    return resolved


def default(defaults: Mapping[str, str | None], name: str, fallback: str) -> str:
    value = defaults.get(name)
    return value if isinstance(value, str) and value else fallback


def configured_path(
    value: str,
    name: str,
    home: Path,
    placeholders: Mapping[str, str] | None = None,
    *, preserve_symlinks: bool = False,
) -> Path:
    variables = placeholders or {}

    def replace(match: re.Match[str]) -> str:
        variable = match.group(1)
        if variable not in variables:
            raise InstallationError(f"{name}: nieznany placeholder {variable}")
        return variables[variable]

    value = re.sub(r"\$\{([A-Z][A-Z0-9_]*)\}", replace, value)
    if value == "~":
        value = str(home)
    elif value.startswith("~/"):
        value = str(home / value[2:])
    return absolute(value, name, preserve_symlinks=preserve_symlinks)

def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)
