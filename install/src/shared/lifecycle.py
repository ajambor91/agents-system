"""Installation provenance, configuration validation and transaction helpers."""
from __future__ import annotations

from dataclasses import fields, replace
import json
import os
from pathlib import Path
from typing import Any, Callable

from ..consts import (
    CONFIGURATION_PATH_FIELDS, CONFIGURATION_BOOLEAN_FIELDS, ENVIRONMENT_FILE,
    ENVIRONMENT_KIND, INSTALLATION_KIND, INSTALLATION_SUCCESS_STATUSES,
    LIFECYCLE_IDENTITY_VARIABLES, MARKER_NAME, SAFE_APP_NAME, SAFE_NAME,
    DEV_RUNTIME_SOCKET_VARIABLES,
)
from ..errors import InstallationError
from ..models import Account, InstallConfiguration
from .shared import absolute, is_below


def require_root(effective_uid: int) -> None:
    if effective_uid != 0:
        raise InstallationError("Operacja lifecycle wymaga uprawnień root")


def environment_values(document: dict[str, Any]) -> dict[str, str]:
    return {item['name']: item['value'] for item in document['variables']}


def validate_environment(document: dict[str, Any]) -> None:
    from manifests import ManifestValidator
    if not isinstance(document, dict) or document.get('kind') != ENVIRONMENT_KIND:
        raise InstallationError(f"Konfiguracja wymaga kind={ENVIRONMENT_KIND}")
    try:
        ManifestValidator.validate(document)
    except (ValueError, TypeError, OSError) as exc:
        raise InstallationError(f"Nieprawidłowa konfiguracja środowiska: {exc}") from exc


def read_environment(raw_path: str | Path) -> dict[str, Any]:
    path = absolute(str(raw_path), 'ENVS')
    if not path.is_file():
        raise InstallationError(f"Brak zwykłego pliku konfiguracji: {path}")
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise InstallationError(f"Nie można odczytać konfiguracji {path}: {exc}") from exc
    validate_environment(document)
    return document


def safe_managed_path(value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value or any(char in value for char in ('\x00', '\r', '\n')):
        raise InstallationError(f"Nieprawidłowa ścieżka {name}")
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or path == Path(path.anchor):
        raise InstallationError(f"Niebezpieczna ścieżka {name}: {value}")
    if any(parent.is_symlink() for parent in path.parents):
        raise InstallationError(f"Ścieżka {name} zawiera dowiązany katalog nadrzędny")
    return path  # Preserve the identity of a managed dev symlink.


def configuration_from_journal(journal: Any, *, package_dir: Path | None = None, verbose: bool = False, require_source: bool = True) -> InstallConfiguration:
    if journal.state.get('status') not in INSTALLATION_SUCCESS_STATUSES:
        raise InstallationError("Wymagany jest dziennik zakończonej instalacji")
    raw = journal.state.get('configuration')
    if not isinstance(raw, dict):
        raise InstallationError("Dziennik nie zawiera konfiguracji instalacji")
    try:
        values = {field.name: raw[field.name] for field in fields(InstallConfiguration)}
        for name in CONFIGURATION_PATH_FIELDS:
            values[name] = safe_managed_path(values[name], name)
        for name in CONFIGURATION_BOOLEAN_FIELDS:
            if type(values[name]) is not bool:
                raise InstallationError(f"Nieprawidłowy boolean: {name}")
        if values['mode'] not in {'system', 'dev'} or not SAFE_APP_NAME.fullmatch(values['app_name']):
            raise InstallationError("Nieprawidłowa tożsamość instalacji")
        for name in ('user_system', 'user_group'):
            if not isinstance(values[name], str) or not SAFE_NAME.fullmatch(values[name]):
                raise InstallationError(f"Nieprawidłowe konto: {name}")
        if values['bash_source'] not in {'true', 'false'}:
            raise InstallationError("Nieprawidłowy BASH_SOURCE")
        invoker = dict(values['invoker'])
        invoker['home'] = safe_managed_path(invoker['home'], 'invoker.home')
        if not SAFE_NAME.fullmatch(invoker['name']) or any(type(invoker[key]) is not int or invoker[key] < 0 for key in ('uid', 'gid')):
            raise InstallationError("Nieprawidłowa tożsamość invokera")
        values['invoker'] = Account(**invoker)
        configuration = InstallConfiguration(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise InstallationError(f"Nieprawidłowa konfiguracja dziennika: {exc}") from exc
    roots = [configuration.install_dir, configuration.config_dir, configuration.data_dir, configuration.runtime_dir]
    for offset, path in enumerate(roots):
        for other in roots[offset + 1:]:
            if is_below(path, other) or is_below(other, path):
                raise InstallationError("Główne katalogi instalacji nie mogą się nakładać")
    source = configuration.package_dir if package_dir is None else absolute(str(package_dir), 'SOURCE', must_exist=True)
    if require_source and not source.is_dir():
        raise InstallationError(f"Brak pakietu źródłowego: {source}")
    return replace(configuration, package_dir=source, force=True, verbose=verbose)


def validate_owned_directory(path: Path, configuration: InstallConfiguration) -> None:
    if not path.exists() and not path.is_symlink():
        return
    marker = path / MARKER_NAME
    if path.is_symlink() or not path.is_dir() or marker.is_symlink():
        raise InstallationError(f"Obcy katalog instalacji: {path}")
    try:
        document = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise InstallationError(f"Brak prawidłowego markera: {path}") from exc
    if (not isinstance(document, dict) or document.get('kind') != INSTALLATION_KIND
            or document.get('app_name') != configuration.app_name
            or document.get('install_dir') != str(configuration.install_dir)):
        raise InstallationError(f"Marker nie należy do tej instalacji: {path}")


def validate_owned_installation(configuration: InstallConfiguration) -> None:
    install = configuration.install_dir
    if configuration.mode == 'dev' and not configuration.clone_repo:
        if not install.is_symlink() or install.resolve() != configuration.package_dir.resolve():
            raise InstallationError(f"Obcy cel instalacji dev: {install}")
    else:
        if not install.is_dir():
            raise InstallationError(f"Brak zainstalowanej aplikacji: {install}")
        validate_owned_directory(install, configuration)
    for path in (configuration.config_dir, configuration.data_dir, configuration.runtime_dir):
        validate_owned_directory(path, configuration)
    if not configuration.config_dir.is_dir():
        raise InstallationError("Brak aktywnej konfiguracji instalacji")


def validate_environment_identity(document: dict[str, Any], configuration: InstallConfiguration, *, previous: dict[str, Any] | None = None) -> None:
    values = environment_values(document)
    expected = {
        'INSTALL_MODE': configuration.mode, 'APP_NAME': configuration.app_name,
        'USER_SYSTEM': configuration.user_system, 'USER_GROUP': configuration.user_group,
    }
    for name, value in expected.items():
        if values[name] != value:
            raise InstallationError(f"{name} nie odpowiada instalacji")
    paths = {
        'APP_DIR': configuration.install_dir, 'APP_CONFIG_DIR': configuration.config_dir,
        'APP_DATA_DIR': configuration.data_dir, 'APP_RUNTIME_DIR': configuration.runtime_dir,
        'USER_SYSTEM_HOME': configuration.user_home,
    }
    for name, path in paths.items():
        if Path(values[name]).resolve(strict=False) != path.resolve(strict=False):
            raise InstallationError(f"{name} nie odpowiada instalacji")
    if previous is not None:
        old = environment_values(previous)
        changed = [name for name in LIFECYCLE_IDENTITY_VARIABLES if values[name] != old[name]]
        if changed:
            raise InstallationError("Reconfigure nie migruje ścieżek ani kont: " + ', '.join(changed))


def transaction(configuration: InstallConfiguration, journal_configuration: dict[str, Any], action: Callable[[Any], dict[str, Any]], *, runner: Callable[..., Any], effective_uid: int) -> dict[str, Any]:
    from ..journal import InstallJournal
    from ..rollback import InstallationRollback
    journal = InstallJournal.create(configuration.app_name, journal_configuration)
    try:
        outputs = action(journal)
        outputs['journal'] = str(journal.root)
        journal.finish('success', outputs=outputs)
        return outputs
    except Exception as exc:
        journal.finish('failed', error=str(exc))
        try:
            InstallationRollback(runner=runner, effective_uid=effective_uid).rollback(journal.root)
        except InstallationError as rollback_error:
            raise InstallationError(f"{exc}; {rollback_error}") from exc
        raise InstallationError(str(exc)) from exc


def managed_commands(journal: Any, configuration: InstallConfiguration) -> list[Path]:
    raw_commands = journal.state.get('outputs', {}).get('commands')
    if not isinstance(raw_commands, list):
        raw_commands = journal.state.get('configuration', {}).get('managed_commands', [])
    result = []
    for raw in raw_commands:
        target = safe_managed_path(raw, 'command')
        if target.parent != configuration.commands_dir or not SAFE_APP_NAME.fullmatch(target.name):
            raise InstallationError(f"Komenda poza instalacją: {target}")
        source = configuration.install_dir / 'host_scripts' / (target.name.replace('-', '_') + '.sh')
        if not source.is_file():
            # Wrapper names may already contain dashes.
            source = configuration.install_dir / 'host_scripts' / (target.name + '.sh')
        if not source.is_file() or not target.is_symlink() or target.resolve() != source.resolve():
            raise InstallationError(f"Obca lub brakująca komenda: {target}")
        result.append(target)
    return result


def lifecycle_journal_configuration(configuration: InstallConfiguration, previous: Any, operation: str) -> dict[str, Any]:
    raw = configuration.public_dict()
    for name in ('unit_path', 'installed_modules_dir', 'installed_modules_file', 'installed_modules_sha256', 'installed_modules_created_parents', 'installer_module_dir'):
        if name in previous.state['configuration']:
            raw[name] = previous.state['configuration'][name]
    raw['managed_commands'] = [str(path) for path in managed_commands(previous, configuration)]
    raw['operation'] = operation
    raw['previous_journal'] = str(previous.root)
    return raw


def validate_managed_unit(path: Path, configuration: InstallConfiguration) -> None:
    if not path.exists() and not path.is_symlink():
        if configuration.mode == 'system':
            raise InstallationError(f"Brak zarządzanej usługi: {path}")
        return
    if path.is_symlink() or not path.is_file():
        raise InstallationError(f"Obca usługa: {path}")
    text = path.read_text(encoding='utf-8')
    if 'Managed by agents-system installer' not in text or f'WorkingDirectory={configuration.install_dir}\n' not in text:
        raise InstallationError(f"Usługa nie należy do instalacji: {path}")


def validate_dev_runtime_stopped(document: dict[str, Any], configuration: InstallConfiguration) -> None:
    if configuration.mode != 'dev':
        return
    values = environment_values(document)
    for name in DEV_RUNTIME_SOCKET_VARIABLES:
        path = Path(values[name])
        if path.exists() or path.is_symlink():
            raise InstallationError(f"Zatrzymaj runtime dev i usuń nieaktywny socket przed operacją lifecycle: {path}")


def renderer_process_environment(configuration: InstallConfiguration, base: dict[str, str]) -> dict[str, str]:
    """Render the resolved installation, without consulting installed get_var wrappers."""
    return {
        **base, 'PATH': os.defpath,
        'APP_NAME': configuration.app_name,
        'USER_SYSTEM': configuration.user_system,
        'USER_GROUP': configuration.user_group,
        'USER_SYSTEM_HOME': str(configuration.user_home),
    }
