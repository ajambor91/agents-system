"""Load and validate the unified Agents System modules manifest."""

from __future__ import annotations

import copy
import json
import keyword
import re
from pathlib import Path
from typing import Any

from ..exceptions import ApiError


NAME = re.compile(r"^[a-z][a-z0-9-]*$")
COMMAND_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
FLAG = re.compile(r"^--[a-z][a-z0-9-]*$")
SHORT_FLAG = re.compile(r"^-[A-Za-z0-9]$")
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ManifestCatalog:
    """Build the console menu in memory from one modules manifest."""

    def __init__(self, manifest_path: Path | None = None) -> None:
        if manifest_path is None:
            repository_root = Path(__file__).resolve().parents[4]
            rendered = repository_root / "resources" / "agents-system.module.json"
            manifest_path = (
                rendered
                if rendered.is_file()
                else repository_root / "resources" / "agents-system.module.template.json"
            )
        self.manifest_path = manifest_path.expanduser().resolve(strict=False)

    def load(self) -> dict[str, Any]:
        source = self._read(self.manifest_path)
        self._validate_manifest(source)
        sections: dict[str, Any] = {}
        for child in source["children"]:
            if not child["is_menu_option"]:
                continue
            name = child["section_name"]
            if name in sections:
                raise ApiError(f"Powtórzona sekcja menu: {name}")
            sections[name] = {
                "schema_version": source["schema_version"],
                "version": source["version"],
                "kind": "asystem-menu-manifest",
                "absolute_path": str(self.manifest_path),
                "module_name": child["module_name"],
                "absolute_module_path": child["absolute_module_path"],
                "section_name": name,
                "menu_name": child["menu_name"],
                "description": child["description"],
                "commands": copy.deepcopy(child["commands"]),
            }
        if not sections:
            raise ApiError(f"Brak modułów menu w {self.manifest_path}")
        return {
            "schema_version": source["schema_version"],
            "version": source["version"],
            "kind": "asystem-app-manifest",
            "app_name": "app_api",
            "absolute_path": str(self.manifest_path),
            "menu_name": "Agents System",
            "description": "Konsola zarządzania systemem i agentami.",
            "sections": sections,
        }

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ApiError(f"Brak manifestu modułów: {path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ApiError(f"Nieprawidłowy manifest modułów {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ApiError(f"Manifest modułów musi być obiektem: {path}")
        return value

    def _validate_manifest(self, value: dict[str, Any]) -> None:
        path = self.manifest_path
        if value.get("schema_version") != 1 or value.get("version") != 1:
            raise ApiError(f"{path}: wymagane schema_version=1 i version=1")
        if value.get("kind") != "agents-system-modules-manifest":
            raise ApiError(f"{path}: wymagane kind=agents-system-modules-manifest")
        if value.get("app_module_name") != "agents-system":
            raise ApiError(f"{path}: app_module_name musi mieć wartość agents-system")
        declared_path = value.get("manifest_absolute_path")
        if path.name.endswith(".template.json"):
            if declared_path != "${MODULES_MANIFEST_PATH}":
                raise ApiError(f"{path}: szablon wymaga placeholdera MODULES_MANIFEST_PATH")
        elif not isinstance(declared_path, str) or Path(declared_path).resolve(strict=False) != path:
            raise ApiError(f"{path}: manifest_absolute_path nie wskazuje tego manifestu")
        children = value.get("children")
        if not isinstance(children, list) or not children:
            raise ApiError(f"{path}: children musi być niepustą tablicą")

        modules: set[str] = set()
        sections: set[str] = set()
        for offset, child in enumerate(children):
            if not isinstance(child, dict):
                raise ApiError(f"{path}: children[{offset}] musi być obiektem")
            module_name = child.get("module_name")
            if (
                not isinstance(module_name, str)
                or not MODULE_NAME.fullmatch(module_name)
                or module_name in modules
            ):
                raise ApiError(f"{path}: nieprawidłowy lub powtórzony module_name")
            modules.add(module_name)
            if not isinstance(child.get("absolute_module_path"), str) or not child["absolute_module_path"].strip():
                raise ApiError(f"{path}: {module_name}.absolute_module_path musi być niepustym tekstem")
            if not isinstance(child.get("is_menu_option"), bool):
                raise ApiError(f"{path}: {module_name}.is_menu_option musi być boolean")
            if not isinstance(child.get("is_runtime"), bool):
                raise ApiError(f"{path}: {module_name}.is_runtime musi być boolean")
            runtimes = child.get("runtime")
            if not isinstance(runtimes, list) or any(
                not isinstance(item, str) or not MODULE_NAME.fullmatch(item)
                for item in runtimes
            ):
                raise ApiError(f"{path}: {module_name}.runtime musi być tablicą")
            if not child["is_menu_option"]:
                continue
            section_name = child.get("section_name")
            if (
                not isinstance(section_name, str)
                or not NAME.fullmatch(section_name)
                or section_name in sections
            ):
                raise ApiError(f"{path}: nieprawidłowe lub powtórzone section_name")
            sections.add(section_name)
            for field in ("menu_name", "description"):
                if not isinstance(child.get(field), str) or not child[field].strip():
                    raise ApiError(f"{path}: {module_name}.{field} musi być niepustym tekstem")
            commands = child.get("commands")
            if not isinstance(commands, list) or not commands:
                raise ApiError(f"{path}: {module_name}.commands musi być niepustą tablicą")
            command_names: set[str] = set()
            for command in commands:
                self._validate_command(command, path, command_names)

    @staticmethod
    def _validate_command(command: Any, path: Path, names: set[str]) -> None:
        if not isinstance(command, dict):
            raise ApiError(f"{path}: element commands musi być obiektem")
        name = command.get("name")
        if not isinstance(name, str) or not COMMAND_NAME.fullmatch(name) or name in names:
            raise ApiError(f"{path}: nieprawidłowa lub powtórzona komenda {name!r}")
        names.add(name)
        method = command.get("method", name.replace("-", "_"))
        if not isinstance(method, str) or not method.isidentifier() or method.startswith("_") or keyword.iskeyword(method):
            raise ApiError(f"{path}: nieprawidłowa publiczna metoda {method!r}")
        for field in ("description", "usage"):
            if not isinstance(command.get(field), str) or not command[field].strip():
                raise ApiError(f"{path}: {name}.{field} musi być niepustym tekstem")
        flags = command.get("flags", [])
        if not isinstance(flags, list):
            raise ApiError(f"{path}: {name}.flags musi być tablicą")
        tokens: set[str] = set()
        for flag in flags:
            if not isinstance(flag, dict):
                raise ApiError(f"{path}: flaga komendy {name} musi być obiektem")
            flag_name = flag.get("name")
            if not isinstance(flag_name, str) or not FIELD_NAME.fullmatch(flag_name):
                raise ApiError(f"{path}: nieprawidłowe name flagi w komendzie {name}")
            for field in ("description", "usage"):
                if not isinstance(flag.get(field), str) or not flag[field].strip():
                    raise ApiError(f"{path}: {name}.{flag_name}.{field} musi być niepustym tekstem")
            long = flag.get("long")
            short = flag.get("short")
            if not isinstance(long, str) or not FLAG.fullmatch(long):
                raise ApiError(f"{path}: nieprawidłowa flaga {long!r}")
            if short is not None and (
                not isinstance(short, str) or not SHORT_FLAG.fullmatch(short)
            ):
                raise ApiError(f"{path}: nieprawidłowa krótka flaga {short!r}")
            aliases = flag.get("aliases", [])
            if not isinstance(aliases, list) or any(
                not isinstance(alias, str) or not FLAG.fullmatch(alias)
                for alias in aliases
            ):
                raise ApiError(f"{path}: nieprawidłowe aliases dla {long}")
            for token in [long, short, *aliases]:
                if token is not None:
                    if token in tokens:
                        raise ApiError(f"{path}: powtórzony token flagi {token}")
                    tokens.add(token)

        groups = command.get("exclusive_groups", [])
        if not isinstance(groups, list):
            raise ApiError(f"{path}: {name}.exclusive_groups musi być tablicą")
        flag_names = {flag["name"] for flag in flags}
        for group in groups:
            if not isinstance(group, dict):
                raise ApiError(f"{path}: {name}: nieprawidłowa grupa flag")
            members = group.get("members")
            if not isinstance(members, list) or not members or any(
                not isinstance(member, str) or member not in flag_names for member in members
            ) or len(set(members)) != len(members):
                raise ApiError(f"{path}: {name}: nieprawidłowe members grupy flag")
            minimum, maximum = group.get("minimum", 0), group.get("maximum", 1)
            if type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= maximum <= len(members):
                raise ApiError(f"{path}: {name}: nieprawidłowe limity grupy flag")


def find_command(section: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((command for command in section["commands"] if command["name"] == name), None)
