#!/usr/bin/env python3
"""Render the managed Agents System environment contract."""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_scripts.common import (  # noqa: E402
    DOUBLE_REFERENCE,
    SAFE_IDENTIFIER,
    SAFE_VARIABLE,
    SHELL_REFERENCE,
    RenderError,
    atomic_json,
    load_name_values,
    load_object,
    require_absolute_directory,
    resolve_values,
)


ACCOUNT_NAME = re.compile(r"^[a-z_][a-z0-9_-]*$")
OBSOLETE_VARIABLES = {
    "REPOSITORIES_DIR", "REPOSITORIES_DIR_FULL", "REPOSITORIES_METADATA",
    "REPOSITORIES_METADATA_FULL", "REPOSITORIES_GENERAL_FILE",
    "REPOSITORIES_GENERAL_HISTORY", "REPOSITORY_DATA_FILE", "REPOSITORY_HISTORY_DIR",
    "REPOSITORY_HISTORY_PATH", "AGENTS_SYSTEM_MODULES_FILE", "AGENTS_SYSTEM_MODULES_PATH",
    "APP_DATA_FULL_DIR", "AGENT_METADATA", "AGENT_METADATA_FULL", "GENERAL_ENV_FILE",
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="render-app-env")
    value.add_argument("-m", "--mode", required=True, choices=("system", "dev"))
    value.add_argument("-d", "--install-dir", required=True)
    value.add_argument("--user-system")
    value.add_argument("--user-group")
    value.add_argument("--user-system-home")
    value.add_argument("--config-dir")
    value.add_argument("--data-dir")
    value.add_argument("--runtime-dir")
    value.add_argument("--bash-source", choices=("true", "false"))
    value.add_argument("-o", "--output")
    value.add_argument("-f", "--force", action="store_true")
    value.add_argument("-v", "--verbose", action="store_true")
    return value


def get_var(name: str) -> str | None:
    """Read one optional bootstrap value without invoking a shell."""
    executable = shutil.which("get_var")
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, name], check=False, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    result = completed.stdout.strip()
    return result or None


def _selected(
    name: str,
    explicit: str | None,
    environment: Mapping[str, str],
    resolver: Callable[[str], str | None],
    defaults: Mapping[str, str | None],
    fallback: str | None = None,
    *,
    prefer_environment: bool = False,
) -> str:
    candidates = (environment.get(name), explicit) if prefer_environment else (explicit,)
    for candidate in candidates:
        if candidate is not None and candidate != "":
            return candidate
    resolved = resolver(name)
    if resolved is not None and resolved != "":
        return resolved
    for candidate in (defaults.get(name), fallback):
        if candidate is not None and candidate != "":
            return candidate
    raise RenderError(f"Brak wymaganej wartości: {name}")


def _validate_source_template(path: Path) -> list[dict[str, Any]]:
    document = load_object(path)
    if document.get("schema_version") != 1 or document.get("kind") != "agents-system-environment":
        raise RenderError("app_env.template.json wymaga schema_version=1 i kind=agents-system-environment")
    variables = document.get("variables")
    if not isinstance(variables, list) or not variables:
        raise RenderError("app_env.template.json: variables musi być niepustą tablicą")
    names: set[str] = set()
    for offset, item in enumerate(variables):
        if not isinstance(item, dict):
            raise RenderError(f"app_env.template.json: variables[{offset}] musi być obiektem")
        name = item.get("name")
        if not isinstance(name, str) or not SAFE_VARIABLE.fullmatch(name) or name in names:
            raise RenderError(f"app_env.template.json: nieprawidłowa lub powtórzona nazwa {name!r}")
        if not isinstance(item.get("value"), str):
            raise RenderError(f"app_env.template.json: {name}.value musi być tekstem")
        names.add(name)
    return variables


def _managed_contract(path: Path) -> list[dict[str, Any]]:
    document = load_object(path)
    if document.get("schema_version") != 1 or document.get("command") != "render-app-env":
        raise RenderError("Nieprawidłowy kontrakt render-app-env")
    variables = document.get("managed_variables")
    if not isinstance(variables, list) or not variables:
        raise RenderError("Kontrakt render-app-env nie zawiera managed_variables")
    names: set[str] = set()
    for offset, item in enumerate(variables):
        if not isinstance(item, dict):
            raise RenderError(f"managed_variables[{offset}] musi być obiektem")
        name = item.get("name")
        if not isinstance(name, str) or not SAFE_VARIABLE.fullmatch(name) or name in names:
            raise RenderError(f"Nieprawidłowa lub powtórzona zmienna kontraktu: {name!r}")
        names.add(name)
    obsolete = sorted(names & OBSOLETE_VARIABLES)
    if obsolete:
        raise RenderError("Kontrakt nadal zawiera wycofane zmienne: " + ", ".join(obsolete))
    return variables


def _normalized_absolute(value: str, name: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise RenderError(f"{name} musi być bezpieczną ścieżką absolutną")
    return str(path.resolve(strict=False))


def _validate_double_placeholders(values: Mapping[str, str]) -> None:
    for name, value in values.items():
        placeholders = DOUBLE_REFERENCE.findall(value)
        unknown = next((placeholder for placeholder in placeholders if placeholder != "agent_name"), None)
        if unknown is not None:
            raise RenderError(f"{name}: nieznany placeholder {{{{{unknown}}}}}")
        if DOUBLE_REFERENCE.search(value.replace("{{agent_name}}", "mimir")):
            raise RenderError(f"{name}: nierozwiązany placeholder")


def _validate_layout(values: Mapping[str, str], mode: str) -> None:
    for name in ("APP_CONFIG_DIR", "APP_DATA_DIR", "INSTALLED_MODULES_DIR", "APP_RUNTIME_DIR"):
        _normalized_absolute(values[name], name)

    expected_agent_paths = {
        "AGENT_CONFIG_DIR_TEMPLATE": "/home/{{agent_name}}/.agents",
        "AGENT_CONFIG_PATH_TEMPLATE": "/home/{{agent_name}}/.agents/config.json",
        "AGENT_RUNTIME_CONFIG_PATH_TEMPLATE": "/home/{{agent_name}}/.agents/runtime.json",
        "AGENT_SHELL_CONFIG_PATH_TEMPLATE": "/home/{{agent_name}}/.agents/shell.json",
        "AGENT_SHELLS_DIR_TEMPLATE": "/home/{{agent_name}}/.agents/shells",
        "AGENT_AGENTRC_PATH_TEMPLATE": "/home/{{agent_name}}/.agents/shells/.agentrc",
        "AGENT_BASHRC_PATH_TEMPLATE": "/home/{{agent_name}}/.agents/shells/.bashrc",
        "AGENT_HISTORY_DIR_TEMPLATE": "/home/{{agent_name}}/.history",
        "AGENT_HISTORY_PATH_TEMPLATE": "/home/{{agent_name}}/.history/history.jsonl",
        "AGENT_INBOX_DIR_TEMPLATE": "/home/{{agent_name}}/.inbox",
        "AGENT_COMMUNICATION_PATH_TEMPLATE": "/home/{{agent_name}}/.inbox/communication.json",
    }
    for name, expected in expected_agent_paths.items():
        if values.get(name) != expected:
            raise RenderError(f"{name} narusza kontrakt katalogów agenta")
    for name in ("APP_DATA_DIR", "APP_RUNTIME_DIR", "AGENT_HISTORY_DIR_TEMPLATE", "AGENT_INBOX_DIR_TEMPLATE"):
        if values[name] == "/etc" or values[name].startswith("/etc/"):
            raise RenderError(f"{name} nie może wskazywać na /etc")


def render(
    *,
    mode: str,
    package_dir: Path,
    install_dir: Path,
    output: Path,
    force: bool,
    user_system: str | None = None,
    user_group: str | None = None,
    user_system_home: str | None = None,
    config_dir: str | None = None,
    data_dir: str | None = None,
    runtime_dir: str | None = None,
    bash_source: str | None = None,
    environment: Mapping[str, str] | None = None,
    value_resolver: Callable[[str], str | None] = get_var,
    verbose: bool = False,
) -> dict[str, Any]:
    if mode not in {"system", "dev"}:
        raise RenderError(f"Nieobsługiwany tryb: {mode}")
    package = require_absolute_directory(str(package_dir), "APPLICATION_ROOT")
    installation = require_absolute_directory(str(install_dir), "INSTALL_DIR")
    defaults_path = package / "resources" / "default_install.json"
    if not defaults_path.is_file():
        defaults_path = package / "install" / "src" / "resources" / "default_install.json"
    defaults = load_name_values(defaults_path)
    template_variables = _validate_source_template(
        package / "resources" / "app_env.template.json"
    )
    managed = _managed_contract(package / "internal_scripts" / "render-app-env.json")
    template_by_name = {item["name"]: item for item in template_variables}
    managed_names = [item["name"] for item in managed]
    if set(template_by_name) != set(managed_names):
        missing = sorted(set(managed_names) - set(template_by_name))
        extra = sorted(set(template_by_name) - set(managed_names))
        raise RenderError(
            "Niezgodność app_env.template.json z kontraktem; "
            f"brak: {missing or '-'}; nadmiarowe: {extra or '-'}"
        )
    supplied_environment = os.environ if environment is None else environment
    selected_bash_source = bash_source or defaults.get("BASH_SOURCE")
    if not isinstance(selected_bash_source, str):
        selected_bash_source = "true" if mode == "dev" else "false"
    selected_bash_source = selected_bash_source.strip().lower()
    if selected_bash_source not in {"true", "false"}:
        raise RenderError("BASH_SOURCE musi mieć wartość true albo false")
    prefer_environment = mode == "dev" and selected_bash_source == "true"

    fallback_user = supplied_environment.get("SUDO_USER") or supplied_environment.get("USER")
    selected_user = _selected(
        "USER_SYSTEM", user_system, supplied_environment, value_resolver, defaults, fallback_user, prefer_environment=prefer_environment
    )
    if not ACCOUNT_NAME.fullmatch(selected_user):
        raise RenderError(f"Nieprawidłowa nazwa USER_SYSTEM: {selected_user!r}")
    try:
        account = pwd.getpwnam(selected_user)
    except KeyError as exc:
        raise RenderError(f"Nie istnieje użytkownik USER_SYSTEM={selected_user}") from exc
    actual_home = str(Path(account.pw_dir).resolve(strict=False))
    selected_home = _selected(
        "USER_SYSTEM_HOME", user_system_home, supplied_environment, value_resolver, {}, actual_home, prefer_environment=prefer_environment
    )
    if _normalized_absolute(selected_home, "USER_SYSTEM_HOME") != actual_home:
        raise RenderError(f"USER_SYSTEM_HOME nie odpowiada bazie passwd dla {selected_user}: {actual_home}")

    try:
        primary_group = grp.getgrgid(account.pw_gid).gr_name
    except KeyError as exc:
        raise RenderError(f"Brak głównej grupy dla USER_SYSTEM={selected_user}") from exc
    selected_group = _selected(
        "USER_GROUP", user_group, supplied_environment, value_resolver,
        defaults, primary_group, prefer_environment=prefer_environment,
    )
    if not ACCOUNT_NAME.fullmatch(selected_group):
        raise RenderError(f"Nieprawidłowa nazwa USER_GROUP: {selected_group!r}")
    try:
        grp.getgrnam(selected_group)
    except KeyError as exc:
        raise RenderError(f"Nie istnieje USER_GROUP={selected_group}") from exc

    app_name = _selected(
        "APP_NAME", None, supplied_environment, value_resolver, defaults,
        prefer_environment=prefer_environment,
    )
    if not SAFE_IDENTIFIER.fullmatch(app_name):
        raise RenderError(f"Nieprawidłowy APP_NAME: {app_name!r}")
    default_paths = {
        "system": {
            "APP_CONFIG_DIR": f"/etc/{app_name}",
            "APP_DATA_DIR": f"/var/lib/{app_name}",
            "APP_RUNTIME_DIR": f"/run/{app_name}",
        },
        "dev": {
            "APP_CONFIG_DIR": f"{actual_home}/.{app_name}/config",
            "APP_DATA_DIR": f"{actual_home}/.{app_name}/data",
            "APP_RUNTIME_DIR": f"{actual_home}/.{app_name}/run",
        },
    }[mode]
    mode_values = {
        "APP_CONFIG_DIR": _normalized_absolute(config_dir or default_paths["APP_CONFIG_DIR"], "APP_CONFIG_DIR"),
        "APP_DATA_DIR": _normalized_absolute(data_dir or default_paths["APP_DATA_DIR"], "APP_DATA_DIR"),
        "APP_RUNTIME_DIR": _normalized_absolute(runtime_dir or default_paths["APP_RUNTIME_DIR"], "APP_RUNTIME_DIR"),
    }
    special = {
        "INSTALL_MODE": mode, "BASH_SOURCE": selected_bash_source, "APP_NAME": app_name,
        "INSTALL_DIR": str(installation), "APP_DIR": str(installation),
        "USER_SYSTEM": selected_user, "USER_GROUP": selected_group,
        "USER_SYSTEM_HOME": actual_home, **mode_values,
    }

    raw: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for item in managed:
        name = item["name"]
        template_item = template_by_name[name]
        value = special.get(name, template_item.get("value"))
        if not isinstance(value, str) or not value:
            raise RenderError(f"Szablon nie definiuje wartości {name}")
        raw[name] = value
        metadata[name] = template_item
    resolved = resolve_values(raw)
    if any(SHELL_REFERENCE.search(value) for value in resolved.values()):
        raise RenderError("Wynik zawiera nierozwiązany placeholder ${NAME}")
    _validate_double_placeholders(resolved)
    _validate_layout(resolved, mode)

    variables: list[dict[str, str]] = []
    for name in raw:
        item = metadata[name]
        example = item.get("example")
        if not isinstance(example, str) or not example:
            example = resolved[name].replace("{{agent_name}}", "mimir")
        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            description = f"Managed Agents System variable {name}."
        variables.append({
            "name": name, "value": resolved[name], "description": description, "example": example
        })

    document = {"schema_version": 1, "kind": "agents-system-environment", "variables": variables}
    atomic_json(output, document, force=force)
    verified = load_object(output)
    verified_names = [item.get("name") for item in verified.get("variables", [])]
    if verified_names != list(raw):
        raise RenderError("Weryfikacja zapisanego app_env.json nie powiodła się")
    if verbose:
        print(f"[render-app-env] zapisano {output}", file=sys.stderr)
    return {"output": str(output.resolve()), "mode": mode, "variables": verified_names, "paths": mode_values}


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    physical_package = Path(__file__).resolve().parents[2]
    package = physical_package
    try:
        output = Path(arguments.output).expanduser() if arguments.output else package / "resources" / "app_env.json"
        result = render(
            mode=arguments.mode, package_dir=package,
            install_dir=Path(arguments.install_dir).expanduser(), output=output,
            force=arguments.force, user_system=arguments.user_system,
            user_group=arguments.user_group, user_system_home=arguments.user_system_home,
            config_dir=arguments.config_dir, data_dir=arguments.data_dir,
            runtime_dir=arguments.runtime_dir, bash_source=arguments.bash_source,
            verbose=arguments.verbose,
        )
    except RenderError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
