"""The installation use-case defined by install/install.json."""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import re
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from .errors import InstallationError
from .journal import InstallJournal
from .models import Account, InstallConfiguration
from .rollback import InstallationRollback


SAFE_NAME = re.compile(r"^[a-z_][a-z0-9_-]*$")
SAFE_APP_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
REQUIRED_DEFAULTS: set[str] = set()
MARKER_NAME = ".agents-system-install.json"
UNIT_ROOT = Path("/etc/systemd/system")


def install_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="install")
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


def _load_defaults(path: Path) -> dict[str, str | None]:
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


def _absolute(value: str, name: str, *, must_exist: bool = False) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise InstallationError(f"{name} musi być bezpieczną ścieżką absolutną")
    resolved = path.resolve(strict=False)
    if must_exist and not resolved.is_dir():
        raise InstallationError(f"{name} nie jest istniejącym katalogiem: {resolved}")
    return resolved


def _default(defaults: Mapping[str, str | None], name: str, fallback: str) -> str:
    value = defaults.get(name)
    return value if isinstance(value, str) and value else fallback


def _configured_path(
    value: str,
    name: str,
    home: Path,
    placeholders: Mapping[str, str] | None = None,
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
    return _absolute(value, name)

def _is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


class Installer:
    """Install the package transactionally, with journal-proven rollback."""

    def __init__(
        self,
        package_dir: Path | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        effective_uid: int | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        unit_root: Path = UNIT_ROOT,
    ) -> None:
        self.package_dir = (package_dir or Path(__file__).resolve().parents[2]).resolve()
        self.environment = dict(os.environ if environment is None else environment)
        self.effective_uid = os.geteuid() if effective_uid is None else effective_uid
        self.runner = runner
        self.unit_root = unit_root
        self.verbose = False

    def execute(self, arguments: argparse.Namespace) -> dict[str, Any]:
        configuration = self.resolve(arguments)
        if self.effective_uid != 0:
            raise InstallationError("Instalator wymaga uprawnień root")
        self.verbose = configuration.verbose
        journal_configuration = configuration.public_dict()
        journal_configuration["unit_path"] = str(
            self.unit_root / f"{configuration.app_name}.service"
        )
        journal = InstallJournal.create(configuration.app_name, journal_configuration)
        try:
            self._log(f"journal: {journal.root}")
            self._preflight(configuration)
            self._log("preflight: ok")
            uid, gid = self._prepare_account(configuration, journal)
            self._log(f"account: {configuration.user_system}:{configuration.user_group}")
            self._install_payload(configuration, journal)
            self._log(f"payload: {configuration.install_dir}")
            self._render_resources(configuration, journal)
            self._log("resources: rendered")
            self._generate_configuration(configuration, journal)
            self._log("configuration class: generated")
            self._prepare_state_directories(configuration, journal, uid, gid)
            self._log("state directories: ready")
            module_record = self._install_module_record(configuration, journal, uid, gid)
            self._log("installed modules: recorded")
            if configuration.mode == "system" or configuration.clone_repo:
                self._set_ownership(configuration.install_dir, uid, gid, configuration.mode)
            self._set_ownership(configuration.config_dir, uid, gid, configuration.mode)
            self._publish_commands(configuration, journal, uid, gid)
            self._log("commands: published")
            if configuration.mode == "system":
                self._install_unit(configuration, journal)
                self._log("systemd: active")
            self._write_absolute_config_pointer(
                configuration, journal, owner_id=uid, group_id=gid
            )
            self._log("src/.env: ready")
            outputs = self._verify(configuration)
            outputs["installed_modules_file"] = str(module_record)
            outputs["journal"] = str(journal.root)
            journal.finish("success", outputs=outputs)
            return outputs
        except Exception as exc:
            journal.finish("failed", error=str(exc))
            try:
                InstallationRollback(runner=self.runner).execute(journal.root)
            except InstallationError as rollback_error:
                raise InstallationError(f"{exc}; {rollback_error}") from exc
            if isinstance(exc, InstallationError):
                raise
            raise InstallationError(str(exc)) from exc

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[install] {message}", file=sys.stderr)

    def resolve(self, arguments: argparse.Namespace) -> InstallConfiguration:
        defaults_path = self.package_dir / "resources" / "default_install.json"
        if not defaults_path.is_file():
            defaults_path = self.package_dir / "install" / "default_install.json"
        defaults = _load_defaults(defaults_path)
        app_name = _default(defaults, "APP_NAME", "agents-system")
        if not SAFE_APP_NAME.fullmatch(app_name):
            raise InstallationError(f"Nieprawidłowy APP_NAME: {app_name!r}")
        self._validate_sources(arguments.mode)

        if arguments.mode == "system":
            forbidden = {
                "--commands-dir": arguments.commands_dir,
                "--clone-repo": arguments.clone_repo,
                "--user-system": arguments.user_system,
                "--user-group": arguments.user_group,
            }
        else:
            forbidden = {
                "--system-user": arguments.system_user,
                "--system-group": arguments.system_group,
            }
            if not arguments.clone_repo:
                forbidden.update({
                    "--user-system": arguments.user_system,
                    "--user-group": arguments.user_group,
                })
            if arguments.clone_repo and arguments.target:
                raise InstallationError("--target nie może być użyte razem z --clone-repo")
        selected_forbidden = [
            name for name, value in forbidden.items() if value not in (None, False)
        ]
        if selected_forbidden:
            raise InstallationError(
                f"Tryb {arguments.mode} nie obsługuje: {', '.join(selected_forbidden)}"
            )

        invoker_name = arguments.invoker or self.environment.get("SUDO_USER")
        if not invoker_name or invoker_name == "root":
            if arguments.mode == "dev":
                raise InstallationError(
                    "Tryb dev uruchomiony bez sudo wymaga --invoker wskazującego użytkownika innego niż root"
                )
            invoker_name = "root"
        invoker = self._account(invoker_name, "INVOKER")
        if arguments.mode == "dev" and invoker.uid == 0:
            raise InstallationError("INVOKER w trybie dev musi być użytkownikiem innym niż root")

        clone_repo = arguments.mode == "dev" and arguments.clone_repo
        dedicated = arguments.mode == "system" or clone_repo
        if arguments.mode == "system":
            user_system = arguments.system_user or _default(defaults, "USER_SYSTEM", "user-system")
            user_group = arguments.system_group or _default(defaults, "USER_GROUP", "user-system")
        elif clone_repo:
            user_system = arguments.user_system or _default(defaults, "USER_SYSTEM", "user-system")
            user_group = arguments.user_group or _default(defaults, "USER_GROUP", "user-system")
        else:
            user_system = invoker.name
            try:
                user_group = grp.getgrgid(invoker.gid).gr_name
            except KeyError as exc:
                raise InstallationError(f"Nie istnieje główna grupa użytkownika {invoker.name}") from exc

        if not SAFE_NAME.fullmatch(user_system) or not SAFE_NAME.fullmatch(user_group):
            raise InstallationError("USER_SYSTEM lub USER_GROUP ma nieprawidłową nazwę")

        if dedicated:
            configured_user = _default(defaults, "USER_SYSTEM", "user-system")
            fallback_home = f"/home/{user_system}"
            configured_home = _default(defaults, "USER_HOME", fallback_home)
            if user_system != configured_user and "USER_HOME" in defaults:
                configured_home = fallback_home
            user_home = _configured_path(configured_home, "USER_HOME", invoker.home)
        else:
            user_home = invoker.home

        path_variables = {
            "APP_NAME": app_name,
            "USER_SYSTEM": user_system,
            "USER_SYSTEM_HOME": str(user_home),
        }
        bash_source = arguments.bash_source or defaults.get("BASH_SOURCE")
        if not isinstance(bash_source, str):
            bash_source = "true" if arguments.mode == "dev" else "false"
        if bash_source not in {"true", "false"}:
            raise InstallationError("BASH_SOURCE musi mieć wartość true albo false")

        if arguments.mode == "system":
            if arguments.target:
                install_dir = _configured_path(
                    arguments.target, "TARGET", invoker.home, path_variables
                )
            else:
                install_root = _configured_path(
                    _default(defaults, "SYSTEM_INSTALL_ROOT", "/opt"),
                    "SYSTEM_INSTALL_ROOT", invoker.home, path_variables,
                )
                install_dir = install_root / app_name
            default_config = f"/etc/{app_name}"
            default_data = f"/var/lib/{app_name}"
            default_runtime = f"/run/{app_name}"
        else:
            if clone_repo:
                install_dir = user_home / app_name
            elif arguments.target:
                install_dir = _configured_path(
                    arguments.target, "TARGET", invoker.home, path_variables
                )
            elif isinstance(defaults.get("SYSTEM_INSTALL_ROOT"), str):
                install_dir = _configured_path(
                    str(defaults["SYSTEM_INSTALL_ROOT"]),
                    "SYSTEM_INSTALL_ROOT", invoker.home, path_variables,
                ) / app_name
            else:
                install_dir = invoker.home / app_name
            dev_root = user_home / f".{app_name}"
            default_config = str(dev_root / "config")
            default_data = str(dev_root / "data")
            default_runtime = str(dev_root / "run")

        config_value = arguments.config_root or _default(
            defaults, "APP_CONFIG_DIR", _default(defaults, "CONFIG_ROOT", default_config)
        )
        data_value = arguments.data_dir or _default(defaults, "APP_DATA_DIR", default_data)
        runtime_value = arguments.runtime_dir or _default(
            defaults, "APP_RUNTIME_DIR", default_runtime
        )
        config_dir = _configured_path(
            config_value, "APP_CONFIG_DIR", user_home, path_variables
        )
        data_dir = _configured_path(
            data_value, "APP_DATA_DIR", user_home, path_variables
        )
        runtime_dir = _configured_path(
            runtime_value, "APP_RUNTIME_DIR", user_home, path_variables
        )
        commands_dir = _configured_path(
            arguments.commands_dir or _default(defaults, "COMMANDS_DIR", "/usr/local/bin"),
            "COMMANDS_DIR", invoker.home, path_variables,
        )
        install_dir = install_dir.resolve(strict=False)
        if install_dir == self.package_dir or _is_below(install_dir, self.package_dir):
            raise InstallationError("Katalog instalacji nie może znajdować się wewnątrz pakietu źródłowego")
        return InstallConfiguration(
            mode=arguments.mode,
            package_dir=self.package_dir,
            app_name=app_name,
            invoker=invoker,
            user_system=user_system,
            user_group=user_group,
            user_home=user_home,
            install_dir=install_dir,
            config_dir=config_dir,
            data_dir=data_dir,
            runtime_dir=runtime_dir,
            commands_dir=commands_dir,
            bash_source=bash_source,
            force=arguments.force,
            dedicated_user=dedicated,
            clone_repo=clone_repo,
            verbose=arguments.verbose,
        )

    def _validate_sources(self, mode: str) -> None:
        required = [
            self.package_dir / "resources" / "app_env.template.json",
            self.package_dir / "resources" / "agents-system.json",
            self.package_dir / "resources" / "agents-system.module.template.json",
            self.package_dir / "internal_scripts" / "render-app-env.sh",
            self.package_dir / "internal_scripts" / "render-modules-manifest.sh",
            self.package_dir / "internal_scripts" / "generate_configuration.sh",
            self.package_dir / "src",
            self.package_dir / "host_scripts",
        ]
        if mode == "system":
            required.append(self.package_dir / "resources" / "system.template.service")
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise InstallationError("Brak wymaganych źródeł instalacji: " + ", ".join(missing))
        for path in required:
            resolved = path.resolve(strict=True)
            if not _is_below(resolved, self.package_dir):
                raise InstallationError(f"Źródło wychodzi poza katalog aplikacji: {path}")

    def _account(self, name: str, label: str) -> Account:
        if not SAFE_NAME.fullmatch(name):
            raise InstallationError(f"{label} ma nieprawidłową nazwę: {name!r}")
        try:
            item = pwd.getpwnam(name)
        except KeyError as exc:
            raise InstallationError(f"Nie istnieje użytkownik {label}={name}") from exc
        home = _absolute(item.pw_dir, f"{label}_HOME")
        return Account(item.pw_name, item.pw_uid, item.pw_gid, home, item.pw_shell)

    def _marker(self, root: Path) -> dict[str, Any] | None:
        path = root / MARKER_NAME
        if root.is_symlink() or path.is_symlink():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("kind") != "agents-system-installation":
            return None
        return value

    def _command_sources(self, configuration: InstallConfiguration, *, installed: bool) -> list[tuple[str, Path]]:
        if installed:
            root = configuration.install_dir / "host_scripts"
        else:
            root = configuration.package_dir / "host_scripts"
        result: list[tuple[str, Path]] = []
        names: set[str] = set()
        for path in sorted(root.glob("*.sh")):
            if not path.is_file() or path.is_symlink():
                raise InstallationError(f"Skrypt komendy musi być zwykłym plikiem: {path}")
            name = path.stem.replace("_", "-")
            if not SAFE_APP_NAME.fullmatch(name) or name in names:
                raise InstallationError(f"Niebezpieczna lub powtórzona nazwa komendy: {name}")
            names.add(name)
            result.append((name, path))
        return result

    def _preflight(self, configuration: InstallConfiguration) -> None:
        existing: list[Path] = []
        if configuration.install_dir.exists() or configuration.install_dir.is_symlink():
            existing.append(configuration.install_dir)
        if (
            configuration.config_dir.exists() or configuration.config_dir.is_symlink()
        ):
            existing.append(configuration.config_dir)
        for state_dir in (configuration.data_dir, configuration.runtime_dir):
            if state_dir.exists() or state_dir.is_symlink():
                existing.append(state_dir)
        unit = self.unit_root / f"{configuration.app_name}.service"
        if configuration.mode == "system" and (unit.exists() or unit.is_symlink()):
            existing.append(unit)
        for name, _ in self._command_sources(configuration, installed=False):
            target = configuration.commands_dir / name
            if target.exists() or target.is_symlink():
                existing.append(target)
        if existing and not configuration.force:
            raise InstallationError(
                "Instalacja już istnieje; użyj --force: " + ", ".join(map(str, existing))
            )
        if not configuration.force:
            return
        install_exists = configuration.install_dir.exists() or configuration.install_dir.is_symlink()
        if configuration.mode == "dev" and not configuration.clone_repo:
            if install_exists and (
                not configuration.install_dir.is_symlink()
                or configuration.install_dir.resolve(strict=False) != configuration.package_dir
            ):
                raise InstallationError(f"Odmowa przejęcia obcego celu dev: {configuration.install_dir}")
        else:
            marker = self._marker(configuration.install_dir)
            if install_exists and (
                configuration.install_dir.is_symlink()
                or marker is None
                or marker.get("app_name") != configuration.app_name
                or marker.get("install_dir") != str(configuration.install_dir)
            ):
                raise InstallationError(f"Odmowa przejęcia obcego katalogu: {configuration.install_dir}")
        if (
            configuration.config_dir.exists() or configuration.config_dir.is_symlink()
        ):
            config_marker = self._marker(configuration.config_dir)
            if (
                configuration.config_dir.is_symlink()
                or config_marker is None
                or config_marker.get("install_dir") != str(configuration.install_dir)
            ):
                raise InstallationError(f"Odmowa przejęcia obcej konfiguracji: {configuration.config_dir}")
        for state_dir in (configuration.data_dir, configuration.runtime_dir):
            if state_dir.exists() or state_dir.is_symlink():
                state_marker = self._marker(state_dir)
                if (
                    state_dir.is_symlink()
                    or state_marker is None
                    or state_marker.get("install_dir") != str(configuration.install_dir)
                ):
                    raise InstallationError(f"Odmowa przejęcia obcego katalogu stanu: {state_dir}")
        for path in existing:
            if path.parent == configuration.commands_dir:
                if not path.is_symlink():
                    raise InstallationError(f"Odmowa nadpisania obcej komendy: {path}")
                target = path.resolve(strict=False)
                owned_root = configuration.install_dir.resolve(strict=False)
                if not _is_below(target, owned_root):
                    raise InstallationError(f"Odmowa nadpisania obcego dowiązania: {path}")
            elif path == unit:
                if path.is_symlink():
                    raise InstallationError(f"Odmowa nadpisania dowiązanej usługi: {path}")
                try:
                    managed = "Managed by agents-system installer" in path.read_text(encoding="utf-8")
                except OSError:
                    managed = False
                if not managed:
                    raise InstallationError(f"Odmowa nadpisania obcej usługi: {path}")
                content = path.read_text(encoding="utf-8")
                if f"WorkingDirectory={configuration.install_dir}" not in content:
                    raise InstallationError(f"Usługa nie należy do tej instalacji: {path}")

    def _run(self, arguments: list[str], *, allowed: set[int] | None = None) -> subprocess.CompletedProcess[str]:
        if self.verbose:
            print("+ " + " ".join(arguments), file=sys.stderr)
        completed = self.runner(arguments, check=False, capture_output=True, text=True)
        if completed.returncode not in (allowed or {0}):
            message = completed.stderr.strip() or completed.stdout.strip()
            raise InstallationError(message or f"Polecenie nie powiodło się: {arguments[0]}")
        return completed

    def _prepare_account(self, configuration: InstallConfiguration, journal: InstallJournal) -> tuple[int, int]:
        if not configuration.dedicated_user:
            return configuration.invoker.uid, configuration.invoker.gid
        try:
            group = grp.getgrnam(configuration.user_group)
        except KeyError:
            arguments = ["groupadd"]
            if configuration.mode == "system":
                arguments.append("--system")
            arguments.append(configuration.user_group)
            self._run(arguments)
            journal.record("created_group", name=configuration.user_group)
            group = grp.getgrnam(configuration.user_group)
        try:
            account = pwd.getpwnam(configuration.user_system)
        except KeyError:
            if configuration.mode == "system":
                arguments = [
                    "useradd", "--system", "--gid", configuration.user_group,
                    "--home-dir", str(configuration.user_home), "--no-create-home",
                    "--shell", "/usr/sbin/nologin", configuration.user_system,
                ]
            else:
                arguments = [
                    "useradd", "--gid", configuration.user_group,
                    "--home-dir", str(configuration.user_home), "--create-home",
                    "--shell", "/bin/bash", configuration.user_system,
                ]
            self._run(arguments)
            journal.record("created_user", name=configuration.user_system)
            account = pwd.getpwnam(configuration.user_system)
        expected_home = configuration.user_home
        if Path(account.pw_dir).resolve(strict=False) != expected_home.resolve(strict=False):
            raise InstallationError(f"Katalog domowy {configuration.user_system} nie odpowiada kontraktowi")
        if configuration.mode == "system" and account.pw_shell != "/usr/sbin/nologin":
            raise InstallationError("Konto systemowe musi używać /usr/sbin/nologin")
        if configuration.mode == "dev" and account.pw_shell.endswith(("nologin", "false")):
            raise InstallationError("Konto dev --clone-repo musi mieć zwykłą powłokę logowania")
        if account.pw_gid != group.gr_gid:
            raise InstallationError("Główna grupa USER_SYSTEM nie odpowiada USER_GROUP")
        if configuration.mode == "dev":
            memberships = set(os.getgrouplist(configuration.invoker.name, configuration.invoker.gid))
            if group.gr_gid not in memberships:
                self._run(["usermod", "-a", "-G", configuration.user_group, configuration.invoker.name])
                journal.record(
                    "added_membership", user=configuration.invoker.name, group=configuration.user_group
                )
        return account.pw_uid, group.gr_gid

    def _replace(self, path: Path, journal: InstallJournal, writer: Callable[[], None]) -> None:
        exists = path.exists() or path.is_symlink()
        if exists:
            backup, metadata = journal.backup(path)
            index = journal.prepare(
                "replaced_path", path=str(path), backup=backup, metadata=metadata
            )
            _remove(path)
        else:
            index = journal.prepare("created_path", path=str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        writer()
        journal.applied(index)

    def _write_marker(self, root: Path, configuration: InstallConfiguration) -> None:
        marker = {
            "schema_version": 1,
            "kind": "agents-system-installation",
            "app_name": configuration.app_name,
            "install_dir": str(configuration.install_dir),
            "package_dir": str(configuration.package_dir),
            "mode": configuration.mode,
        }
        target = root / MARKER_NAME
        temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
        try:
            temporary.write_text(
                json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            temporary.chmod(0o640)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _atomic_copy(source: Path, target: Path, *, mode: int | None = None) -> None:
        temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
        try:
            shutil.copy2(source, temporary)
            if mode is not None:
                temporary.chmod(mode)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _atomic_link(source: Path, target: Path) -> None:
        temporary = target.with_name(f".{target.name}.{secrets.token_hex(4)}.tmp")
        try:
            temporary.symlink_to(source)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _install_payload(self, configuration: InstallConfiguration, journal: InstallJournal) -> None:
        def write_clone() -> None:
            shutil.copytree(configuration.package_dir, configuration.install_dir, symlinks=True)
            self._write_marker(configuration.install_dir, configuration)

        def write_dev_link() -> None:
            configuration.install_dir.symlink_to(configuration.package_dir, target_is_directory=True)

        def write_system() -> None:
            configuration.install_dir.mkdir(mode=0o750)
            shutil.copytree(configuration.package_dir / "src", configuration.install_dir / "src", symlinks=True)
            shutil.copytree(
                configuration.package_dir / "internal_scripts",
                configuration.install_dir / "internal_scripts",
                symlinks=True,
            )
            shutil.copytree(
                configuration.package_dir / "host_scripts",
                configuration.install_dir / "src" / "host-scripts",
                symlinks=False,
            )
            # Public wrappers retain their package-root-relative contract.
            shutil.copytree(
                configuration.package_dir / "host_scripts",
                configuration.install_dir / "host_scripts",
                symlinks=False,
            )
            readme = configuration.package_dir / "README.md"
            if readme.is_file():
                shutil.copy2(readme, configuration.install_dir / "src" / "README.md")
            docs = configuration.package_dir / "docs"
            if docs.is_dir():
                shutil.copytree(docs, configuration.install_dir / "src" / "docs", symlinks=True)
            self._write_marker(configuration.install_dir, configuration)

        self._replace(
            configuration.install_dir,
            journal,
            write_system if configuration.mode == "system"
            else write_clone if configuration.clone_repo
            else write_dev_link,
        )

    def _render_resources(self, configuration: InstallConfiguration, journal: InstallJournal) -> None:
        if configuration.mode == "dev":
            rendered_root = configuration.install_dir / "resources"
            rendered_root.mkdir(parents=True, exist_ok=True)
        else:
            rendered_root = journal.root / "rendered"
            rendered_root.mkdir(mode=0o700)

        app_env = rendered_root / "app_env.json"
        env_arguments = [
            str(configuration.package_dir / "internal_scripts" / "render-app-env.sh"),
            "--mode", configuration.mode,
            "--install-dir", str(configuration.install_dir),
            "--user-system", configuration.user_system,
            "--user-group", configuration.user_group,
            "--user-system-home", str(configuration.user_home),
            "--config-dir", str(configuration.config_dir),
            "--data-dir", str(configuration.data_dir),
            "--runtime-dir", str(configuration.runtime_dir),
            "--bash-source", configuration.bash_source,
            "--output", str(app_env), "--force",
        ]
        self._run(env_arguments)

        try:
            environment_document = json.loads(app_env.read_text(encoding="utf-8"))
            environment_values = {
                item["name"]: item["value"]
                for item in environment_document["variables"]
            }
            app_dir = _absolute(
                environment_values["APP_DIR"], "APP_DIR", must_exist=True
            )
            modules_dir = _absolute(environment_values["MODULES_DIR"], "MODULES_DIR")
            manifest_file = environment_values["MODULES_MANIFEST_FILE"]
            manifest_path = _absolute(
                environment_values["MODULES_MANIFEST_PATH"], "MODULES_MANIFEST_PATH"
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InstallationError(f"Nieprawidłowy wyrenderowany app_env.json: {exc}") from exc
        if app_dir != configuration.install_dir.resolve(strict=False):
            raise InstallationError("APP_DIR nie wskazuje katalogu zainstalowanej aplikacji")
        if not isinstance(manifest_file, str) or Path(manifest_file).name != manifest_file:
            raise InstallationError("MODULES_MANIFEST_FILE musi być samą nazwą pliku")
        if manifest_path != (configuration.config_dir / manifest_file).resolve(strict=False):
            raise InstallationError(
                "MODULES_MANIFEST_PATH nie odpowiada APP_CONFIG_DIR/MODULES_MANIFEST_FILE"
            )

        modules_manifest = rendered_root / "agents-system.module.json"
        self._run([
            str(configuration.package_dir / "internal_scripts" / "render-modules-manifest.sh"),
            "--app-dir", str(app_dir),
            "--modules-dir", str(modules_dir),
            "--manifest-path", str(manifest_path),
            "--output", str(modules_manifest),
            "--force",
        ])

        package_resources = configuration.install_dir / "resources"
        if configuration.mode == "system":
            package_resources.mkdir(parents=True, exist_ok=True)
            package_app_env = package_resources / app_env.name
            package_manifest = package_resources / modules_manifest.name
            self._atomic_copy(app_env, package_app_env, mode=0o640)
            self._atomic_copy(modules_manifest, package_manifest, mode=0o640)
        else:
            package_app_env = app_env
            package_manifest = modules_manifest

        compatibility_resources = configuration.install_dir / "src" / "resources"
        compatibility_resources.mkdir(parents=True, exist_ok=True)
        for source in (package_app_env, package_manifest):
            target = compatibility_resources / source.name
            _remove(target)
            self._atomic_link(source, target)

        def write_config() -> None:
            configuration.config_dir.mkdir(mode=0o750)
            self._atomic_copy(
                package_app_env, configuration.config_dir / package_app_env.name, mode=0o640
            )
            self._atomic_copy(
                package_manifest, configuration.config_dir / manifest_file, mode=0o640
            )
            self._write_marker(configuration.config_dir, configuration)

        self._replace(configuration.config_dir, journal, write_config)

    def _generate_configuration(
        self, configuration: InstallConfiguration, journal: InstallJournal
    ) -> Path:
        """Generate the installed runtime Configuration from the active app_env.json."""
        source = (configuration.config_dir / "app_env.json").resolve(strict=False)
        script = configuration.install_dir / "internal_scripts" / "generate_configuration.sh"
        if not script.is_file():
            raise InstallationError(f"Brak generatora Configuration w paczce: {script}")
        target = (
            configuration.install_dir
            / "src"
            / "lib"
            / "configuration"
            / "configuration.py"
        )

        def write_configuration() -> None:
            self._run([str(script), "--source", str(source)])
            if not target.is_file():
                raise InstallationError(
                    f"Generator nie utworzył klasy Configuration: {target}"
                )

        self._replace(target, journal, write_configuration)
        return target

    def _prepare_state_directories(
        self,
        configuration: InstallConfiguration,
        journal: InstallJournal,
        uid: int,
        gid: int,
    ) -> None:
        for path in (configuration.data_dir, configuration.runtime_dir):
            if path.exists():
                metadata = path.stat()
                if not path.is_dir() or path.is_symlink():
                    raise InstallationError(f"Katalog stanu ma nieprawidłowy typ: {path}")
                if metadata.st_uid != uid or metadata.st_gid != gid:
                    raise InstallationError(f"Katalog stanu ma obcego właściciela: {path}")
                continue
            index = journal.prepare("created_path", path=str(path))
            path.mkdir(parents=True, mode=0o750)
            self._write_marker(path, configuration)
            os.chown(path, uid, gid)
            os.chown(path / MARKER_NAME, uid, gid)
            journal.applied(index)

    def _install_module_record(
        self, configuration: InstallConfiguration, journal: InstallJournal, uid: int, gid: int
    ) -> Path:
        source = configuration.package_dir / "resources" / "agents-system.json"
        try:
            document = json.loads((configuration.config_dir / "app_env.json").read_text(encoding="utf-8"))
            values = {item["name"]: item["value"] for item in document["variables"]}
            raw_path = values["INSTALLED_MODULES_DIR"]
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError("INSTALLED_MODULES_DIR musi być niepustym tekstem")
            path = Path(raw_path).expanduser()
            for component in (path, *path.parents):
                if component.is_symlink():
                    raise InstallationError(f"Katalog modułów zawiera dowiązanie: {component}")
            directory = _absolute(raw_path, "INSTALLED_MODULES_DIR")
            record = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or not isinstance(record.get("modules"), list):
                raise ValueError("agents-system.json wymaga tablicy modules")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise InstallationError(f"Nie można przygotować listy zainstalowanych modułów: {exc}") from exc
        if directory.exists() and not directory.is_dir():
            raise InstallationError(f"INSTALLED_MODULES_DIR nie jest katalogiem: {directory}")
        target = directory / "agents-system.json"
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise InstallationError(f"Nieprawidłowy cel listy modułów: {target}")
        if target.exists() and not configuration.force:
            raise InstallationError(f"Lista modułów już istnieje; użyj --force: {target}")
        missing = []
        parent = directory
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        journal.state["configuration"].update({
            "installed_modules_dir": str(directory),
            "installed_modules_file": str(target),
            "installed_modules_created_parents": [str(path) for path in missing if path != directory],
        })
        journal._write()
        for path in reversed(missing):
            index = journal.prepare("created_path", path=str(path))
            path.mkdir(mode=0o750)
            os.chown(path, uid, gid)
            journal.applied(index)

        def write_record() -> None:
            self._atomic_copy(source, target, mode=0o640)
            os.chown(target, uid, gid)

        self._replace(target, journal, write_record)
        return target

    def _publish_commands(
        self, configuration: InstallConfiguration, journal: InstallJournal, owner_id: int, group_id: int
    ) -> None:
        configuration.commands_dir.mkdir(parents=True, exist_ok=True)
        for name, source in self._command_sources(configuration, installed=True):
            # A plain dev install points at the current checkout. Publishing a
            # command must not mutate files owned by the developer.
            if configuration.mode == "system" or configuration.clone_repo:
                os.chmod(source, 0o770)
                os.chown(source, owner_id, group_id)
            target = configuration.commands_dir / name

            def write_link(target: Path = target, source: Path = source) -> None:
                self._atomic_link(source, target)

            self._replace(target, journal, write_link)

    def _service_state(self, unit: str) -> dict[str, bool]:
        enabled = self._run(["systemctl", "is-enabled", unit], allowed={0, 1, 3, 4})
        active = self._run(["systemctl", "is-active", unit], allowed={0, 1, 3, 4})
        return {"enabled": enabled.returncode == 0, "active": active.returncode == 0}

    def _install_unit(self, configuration: InstallConfiguration, journal: InstallJournal) -> None:
        unit_name = f"{configuration.app_name}.service"
        journal.record("service_state", unit=unit_name, **self._service_state(unit_name))
        env_path = configuration.config_dir / "app_env.json"
        values = {
            item["name"]: item["value"]
            for item in json.loads(env_path.read_text(encoding="utf-8"))["variables"]
        }
        context = {
            **values,
            "APP_NAME": configuration.app_name,
            "APP_DIR": str(configuration.install_dir),
            "USER_SYSTEM": configuration.user_system,
            "USER_GROUP": configuration.user_group,
            "PYTHON_BIN": sys.executable,
        }
        template = (configuration.package_dir / "resources" / "system.template.service").read_text(
            encoding="utf-8"
        )
        for name, value in context.items():
            template = template.replace("{{" + name + "}}", value)
        if re.search(r"\{\{[^{}]+\}\}", template):
            raise InstallationError("Szablon usługi zawiera nierozwiązany placeholder")
        rendered = journal.root / unit_name
        rendered.write_text(template, encoding="utf-8")
        rendered.chmod(0o644)
        self._run(["systemd-analyze", "verify", str(rendered)])
        package_unit = configuration.install_dir / "system" / unit_name
        package_unit.parent.mkdir(mode=0o750)
        shutil.copy2(rendered, package_unit)
        account = pwd.getpwnam(configuration.user_system)
        group = grp.getgrnam(configuration.user_group)
        os.chown(package_unit.parent, account.pw_uid, group.gr_gid)
        os.chown(package_unit, account.pw_uid, group.gr_gid)
        package_unit.chmod(0o640)
        unit_path = self.unit_root / unit_name
        self._replace(
            unit_path,
            journal,
            lambda: self._atomic_copy(rendered, unit_path, mode=0o644),
        )
        self._run(["systemctl", "daemon-reload"])
        journal.record("daemon_reload")
        self._run(["systemctl", "enable", "--now", unit_name])
        journal.record("service_enabled", unit=unit_name)

    def _write_absolute_config_pointer(
        self,
        configuration: InstallConfiguration,
        journal: InstallJournal,
        *,
        owner_id: int,
        group_id: int,
    ) -> Path:
        """Write the final one-variable src/.env after all other mutations."""
        app_env_path = (configuration.config_dir / "app_env.json").resolve(strict=False)
        try:
            document = json.loads(app_env_path.read_text(encoding="utf-8"))
            values = {
                item["name"]: item["value"]
                for item in document["variables"]
            }
            configured_path = values["APP_ENV_PATH"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InstallationError(
                f"Nie można wyznaczyć APP_ENV_PATH dla src/.env: {exc}"
            ) from exc
        if not isinstance(configured_path, str) or any(
            character in configured_path for character in ("\x00", "\r", "\n")
        ):
            raise InstallationError("APP_ENV_PATH nie może zostać zapisany w src/.env")
        resolved_configured_path = _absolute(
            configured_path, "APP_ENV_PATH"
        )
        if resolved_configured_path != app_env_path:
            raise InstallationError(
                "APP_ENV_PATH nie wskazuje zainstalowanego app_env.json"
            )

        source_root = (configuration.install_dir / "src").resolve(strict=False)
        if not source_root.is_dir():
            raise InstallationError(f"Brak katalogu źródłowego aplikacji: {source_root}")
        target = source_root / ".env"
        content = f"ABSOLUTE_CONFIG_PATH={configured_path}\n"

        def write_env() -> None:
            temporary = target.with_name(
                f".{target.name}.{secrets.token_hex(4)}.tmp"
            )
            try:
                with temporary.open("x", encoding="utf-8") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.chmod(0o640)
                os.chown(temporary, owner_id, group_id)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)

        self._replace(target, journal, write_env)
        return target

    def _set_ownership(self, root: Path, uid: int, gid: int, mode: str) -> None:
        if not root.exists():
            return
        for path in [root, *root.rglob("*")]:
            if path.is_symlink():
                os.lchown(path, uid, gid)
                continue
            os.chown(path, uid, gid)
            current = path.stat().st_mode
            if mode == "system":
                if path.is_dir():
                    os.chmod(path, 0o750)
                elif current & stat.S_IXUSR:
                    os.chmod(path, 0o750)
                else:
                    os.chmod(path, 0o640)

    def _verify(self, configuration: InstallConfiguration) -> dict[str, Any]:
        if configuration.mode == "dev" and not configuration.clone_repo:
            if (
                not configuration.install_dir.is_symlink()
                or configuration.install_dir.resolve(strict=False) != configuration.package_dir
            ):
                raise InstallationError("Nieprawidłowe dowiązanie instalacji dev")
        elif self._marker(configuration.install_dir) is None:
            raise InstallationError("Brak znacznika zainstalowanej aplikacji")
        resources = configuration.config_dir
        app_env_path = resources / "app_env.json"
        try:
            app_env_document = json.loads(app_env_path.read_text(encoding="utf-8"))
            environment_values = {
                item["name"]: item["value"]
                for item in app_env_document["variables"]
            }
            configured_app_env_path = Path(
                environment_values["APP_ENV_PATH"]
            ).resolve(strict=False)
            if configured_app_env_path != app_env_path.resolve(strict=False):
                raise ValueError("APP_ENV_PATH nie wskazuje zainstalowanego app_env.json")
            manifest_name = environment_values["MODULES_MANIFEST_FILE"]
            manifest_path = resources / manifest_name
            if Path(environment_values["MODULES_MANIFEST_PATH"]) != manifest_path:
                raise ValueError(
                    "MODULES_MANIFEST_PATH nie odpowiada APP_CONFIG_DIR/MODULES_MANIFEST_FILE"
                )
            modules_document = json.loads(manifest_path.read_text(encoding="utf-8"))
            if modules_document.get("kind") != "agents-system-modules-manifest":
                raise ValueError("nieprawidłowe kind manifestu modułów")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InstallationError(f"Nieprawidłowe zasoby w {resources}: {exc}") from exc
        env_path = configuration.install_dir / "src" / ".env"
        expected_env = (
            f"ABSOLUTE_CONFIG_PATH={environment_values['APP_ENV_PATH']}\n"
        )
        try:
            env_content = env_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise InstallationError(f"Nie można odczytać {env_path}: {exc}") from exc
        if env_content != expected_env:
            raise InstallationError(
                f"{env_path} musi zawierać wyłącznie ABSOLUTE_CONFIG_PATH"
            )

        commands: list[str] = []
        for name, source in self._command_sources(configuration, installed=True):
            target = configuration.commands_dir / name
            if not target.is_symlink() or target.resolve(strict=False) != source.resolve(strict=False):
                raise InstallationError(f"Nieprawidłowe dowiązanie komendy: {target}")
            commands.append(str(target))
        if configuration.mode == "system":
            self._run(["systemctl", "is-active", f"{configuration.app_name}.service"])
        return {
            "status": "installed",
            "mode": configuration.mode,
            "install_dir": str(configuration.install_dir),
            "config_dir": str(configuration.config_dir),
            "environment_file": str(configuration.install_dir / "src" / ".env"),
            "commands": commands,
            "service": f"{configuration.app_name}.service" if configuration.mode == "system" else None,
        }
