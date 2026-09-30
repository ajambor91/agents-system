"""Validation and explicit publication of Agents System environment values."""

from __future__ import annotations

import json
import os
import pwd
import re
import shlex
import sys
from pathlib import Path
from typing import Any, TextIO

from ..errors import ConfigurationError


VARIABLE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
REFERENCE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
BOOLEAN = {"0", "1", "false", "true", "no", "yes", "off", "on"}


class EnvironmentService:
    """Keep the external environment API without automatic application activation."""

    def __init__(self, repository_root: Path | None = None) -> None:
        self.repository_root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
        repository_resources = self.repository_root / "resources"
        installed_resources = self.repository_root / "src" / "resources"
        self.resources = (
            repository_resources
            if repository_resources.is_dir() or not installed_resources.is_dir()
            else installed_resources
        )
        self.template_path = self.resources / "app_env.template.json"
        self.local_path = self.resources / "app_env.json"

    def read_document(self, path: Path) -> dict[str, Any]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"Brak pliku konfiguracji: {path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Nie można odczytać konfiguracji {path}: {exc}") from exc
        return self.validate(document, source=path)

    def validate(self, document: Any, *, source: Path | str = "konfiguracja") -> dict[str, Any]:
        if not isinstance(document, dict) or document.get("schema_version") != 1:
            raise ConfigurationError(f"{source}: wymagany schema_version równy 1")
        if document.get("kind") != "agents-system-environment":
            raise ConfigurationError(f"{source}: nieprawidłowe kind")
        variables = document.get("variables")
        if not isinstance(variables, list) or not variables:
            raise ConfigurationError(f"{source}: variables musi być niepustą tablicą")
        names: set[str] = set()
        for offset, item in enumerate(variables):
            if not isinstance(item, dict):
                raise ConfigurationError(f"{source}: variables[{offset}] musi być obiektem")
            name = item.get("name")
            if not isinstance(name, str) or not VARIABLE_NAME.fullmatch(name) or name in names:
                raise ConfigurationError(f"{source}: nieprawidłowa lub powtórzona nazwa {name!r}")
            names.add(name)
            for field in ("value", "description", "example"):
                if not isinstance(item.get(field), str) or (field != "value" and not item[field].strip()):
                    raise ConfigurationError(f"{source}: {name}.{field} musi być tekstem")
        values = self.resolve(document)
        self._validate_paths(values, source)
        return document

    @staticmethod
    def _validate_paths(values: dict[str, str], source: Path | str) -> None:
        required = {
            "INSTALL_MODE", "BASH_SOURCE", "APP_NAME", "APP_DIR",
            "USER_SYSTEM", "USER_SYSTEM_HOME", "APP_CONFIG_DIR",
            "APP_DATA_DIR", "APP_RUNTIME_DIR", "APP_ENV_FILE", "APP_ENV_PATH",
        }
        missing = sorted(required - values.keys())
        if missing:
            raise ConfigurationError(f"{source}: brak wymaganych zmiennych: {', '.join(missing)}")
        if values["INSTALL_MODE"] not in {"dev", "system"}:
            raise ConfigurationError(f"{source}: INSTALL_MODE musi mieć wartość dev albo system")
        if values["BASH_SOURCE"].strip().lower() not in BOOLEAN:
            raise ConfigurationError(f"{source}: BASH_SOURCE musi mieć wartość boolean")
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", values["USER_SYSTEM"]):
            raise ConfigurationError(f"{source}: USER_SYSTEM nie jest poprawną nazwą użytkownika")
        for name in (
            "USER_SYSTEM_HOME", "APP_DIR", "APP_CONFIG_DIR", "APP_DATA_DIR",
            "APP_RUNTIME_DIR", "APP_ENV_PATH",
        ):
            path = Path(values[name])
            if not path.is_absolute() or ".." in path.parts:
                raise ConfigurationError(f"{source}: {name} musi być bezpieczną ścieżką absolutną")
        if not values["APP_ENV_FILE"] or Path(values["APP_ENV_FILE"]).name != values["APP_ENV_FILE"]:
            raise ConfigurationError(f"{source}: APP_ENV_FILE musi być samą nazwą pliku")
        if Path(values["APP_ENV_PATH"]) != Path(values["APP_CONFIG_DIR"]) / values["APP_ENV_FILE"]:
            raise ConfigurationError(
                f"{source}: APP_ENV_PATH musi odpowiadać APP_CONFIG_DIR/APP_ENV_FILE"
            )

    def resolve(self, document: dict[str, Any]) -> dict[str, str]:
        raw = {item["name"]: item["value"] for item in document["variables"]}
        resolved: dict[str, str] = {}

        def visit(name: str, stack: tuple[str, ...]) -> str:
            if name in resolved:
                return resolved[name]
            if name not in raw:
                raise ConfigurationError(f"Nieznany placeholder ${{{name}}}")
            if name in stack:
                raise ConfigurationError("Cykl placeholderów: " + " -> ".join((*stack, name)))
            value = REFERENCE.sub(lambda match: visit(match.group(1), (*stack, name)), raw[name])
            resolved[name] = value
            return value

        for variable_name in raw:
            visit(variable_name, ())
        return resolved

    def active_path(self) -> Path:
        bootstrap = self.read_document(self.local_path if self.local_path.is_file() else self.template_path)
        values = self.resolve(bootstrap)
        return self.local_path if values["INSTALL_MODE"] == "dev" else Path(values["APP_ENV_PATH"])

    def selected_path(self, *, local: bool = False, file: str | None = None) -> Path:
        if file:
            return Path(file).expanduser().resolve()
        return self.local_path if local else self.active_path()

    def initialize(
        self,
        *,
        use_default: bool,
        file: str | None,
        interactive: bool,
        force: bool = False,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> dict[str, Any]:
        source = self.template_path if use_default or interactive else Path(str(file)).expanduser().resolve()
        document = self.read_document(source)
        if interactive:
            document = self._interactive(document, input_stream or sys.stdin, output_stream or sys.stderr)
        return self.publish(document, source=str(source), force=force)

    def publish(self, document: dict[str, Any], *, source: str, force: bool = False) -> dict[str, Any]:
        document = self.validate(document, source=source)
        values = self.resolve(document)
        self._atomic_json(self.local_path, document)
        if values["INSTALL_MODE"] == "dev":
            central = self.local_path
            export_path = self.local_path.parent / "environment.sh"
        else:
            central = Path(values["APP_ENV_PATH"])
            self._validate_link_target(central, self.local_path, force=force)
            self._prepare_owned_directory(central.parent, values["USER_SYSTEM"])
            self._link(central, self.local_path, force=force)
            export_path = Path(values["APP_CONFIG_DIR"]) / "environment.sh"
        self._atomic_text(export_path, self.render_shell_integration(values), mode=0o644)
        profile = (
            self._write_profile(values)
            if values["INSTALL_MODE"] != "dev" and os.geteuid() == 0
            else None
        )
        return {
            "source": source,
            "local": str(self.local_path),
            "central": str(central),
            "export_file": str(export_path),
            "profile": str(profile) if profile else None,
            "variables": len(values),
        }

    def load_values(self, *, local: bool = False, file: str | None = None) -> dict[str, str]:
        return self.resolve(self.read_document(self.selected_path(local=local, file=file)))

    def load_into_environment(self, *, optional: bool = True) -> dict[str, str]:
        """Explicit compatibility API; dev applications never activate it."""
        try:
            values = self.load_values()
        except ConfigurationError:
            if optional:
                return {}
            raise
        if values.get("INSTALL_MODE") == "dev":
            return {}
        os.environ.update({name: value for name, value in values.items() if name != "BASH_SOURCE"})
        return values

    def get(self, name: str | None, *, local: bool = False) -> str | dict[str, str]:
        values = self.load_values(local=local)
        if name is None:
            return values
        if not VARIABLE_NAME.fullmatch(name):
            raise ConfigurationError(f"Nieprawidłowa nazwa zmiennej: {name}")
        if name not in values:
            raise ConfigurationError(f"Brak zmiennej: {name}")
        return values[name]

    @staticmethod
    def render_exports(values: dict[str, str]) -> str:
        # BASH_SOURCE is a Bash-owned array; it is a JSON policy switch, not an export.
        return "".join(
            f"export {name}={shlex.quote(value)}\n"
            for name, value in sorted(values.items())
            if name != "BASH_SOURCE"
        )

    @staticmethod
    def render_shell_integration(values: dict[str, str]) -> str:
        return EnvironmentService.render_exports(values) + """
# Load a selected Agents System environment into this shell.
asystem_env_export() {
    case "${1-}" in
        -h|--help)
            command /usr/local/bin/asystem_env_export "$@"
            return $?
            ;;
    esac

    local _asystem_env_exports
    _asystem_env_exports="$(command /usr/local/bin/asystem_env_export "$@")" || return $?
    eval "$_asystem_env_exports"
}
"""

    def _interactive(self, document: dict[str, Any], input_stream: TextIO, output: TextIO) -> dict[str, Any]:
        if not input_stream.isatty():
            raise ConfigurationError("Tryb --interactive wymaga terminala")
        for item in document["variables"]:
            print(f"{item['name']}: {item['description']}", file=output)
            print(f"  przykład: {item['example']}", file=output)
            print(f"  wartość [{item['value']}]: ", end="", file=output, flush=True)
            entered = input_stream.readline()
            if entered == "":
                raise ConfigurationError("Przerwano konfigurację interaktywną")
            entered = entered.rstrip("\n")
            if entered:
                item["value"] = entered
        return self.validate(document, source="wejście interaktywne")

    def _atomic_json(self, path: Path, document: dict[str, Any]) -> None:
        self._atomic_text(path, json.dumps(document, ensure_ascii=False, indent=2) + "\n", mode=0o640)

    @staticmethod
    def _atomic_text(path: Path, content: str, *, mode: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
        try:
            temporary.write_text(content, encoding="utf-8")
            temporary.chmod(mode)
            if os.geteuid() == 0:
                parent = path.parent.stat()
                os.chown(temporary, parent.st_uid, parent.st_gid)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _validate_link_target(destination: Path, source: Path, *, force: bool) -> None:
        if destination.is_symlink() and destination.resolve(strict=False) == source.resolve():
            return
        if destination.exists() and not destination.is_symlink():
            if destination.is_dir():
                raise ConfigurationError(f"Cel konfiguracji jest katalogiem: {destination}")
            if not force:
                raise ConfigurationError(f"Nie nadpiszę zwykłego pliku bez --force: {destination}")

    @staticmethod
    def _link(destination: Path, source: Path, *, force: bool) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink() and destination.resolve(strict=False) == source.resolve():
            return
        EnvironmentService._validate_link_target(destination, source, force=force)
        temporary = destination.with_name(destination.name + f".tmp-{os.getpid()}")
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(source.resolve())
        temporary.replace(destination)

    @staticmethod
    def _prepare_owned_directory(path: Path, username: str) -> None:
        path.mkdir(parents=True, exist_ok=True)
        if os.geteuid() != 0:
            return
        try:
            account = pwd.getpwnam(username)
        except KeyError as exc:
            raise ConfigurationError(f"Nie istnieje użytkownik USER_SYSTEM={username}") from exc
        os.chown(path, account.pw_uid, account.pw_gid)

    @staticmethod
    def _write_profile(values: dict[str, str]) -> Path:
        profile = Path("/etc/profile.d/agents-system.sh")
        content = "# Generated by asystem_env_init. Do not edit.\n" + EnvironmentService.render_shell_integration(values)
        EnvironmentService._atomic_text(profile, content, mode=0o644)
        return profile
