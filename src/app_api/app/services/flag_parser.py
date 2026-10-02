"""Validate manifest-defined command flags."""

from typing import Any
from ..exceptions import ApiError


class FlagParser:
    @staticmethod
    def parse(command: dict[str, Any], argv: list[str]) -> dict[str, Any]:
        by_token: dict[str, dict[str, Any]] = {}
        for flag in command.get("flags", []):
            for token in (flag.get("short"), flag["long"], *flag.get("aliases", [])):
                if token:
                    by_token[token] = flag
        values: dict[str, Any] = {}
        positionals = iter(command.get("positionals", []))
        positional_only = False
        index = 0
        while index < len(argv):
            token = argv[index]
            if token == "--" and not positional_only:
                positional_only = True
                index += 1
                continue
            inline: str | None = None
            lookup = token
            if token.startswith("--") and "=" in token:
                lookup, inline = token.split("=", 1)
            definition = None if positional_only else by_token.get(lookup)
            if definition is None:
                if token.startswith("-") and not positional_only:
                    raise ApiError(f"Nieznana flaga dla {command['name']}: {lookup}")
                definition = next(positionals, None)
                if definition is None:
                    raise ApiError(f"Nieoczekiwany argument dla {command['name']}: {token}")
                if definition["name"] in values:
                    raise ApiError(f"Argument {definition['name']} został podany więcej niż raz")
                values[definition["name"]] = FlagParser.convert(definition, token)
                index += 1
                continue
            name = definition["name"]
            if name in values:
                raise ApiError(f"Flaga {definition['long']} została podana więcej niż raz")
            if definition.get("takes_value"):
                if inline is None:
                    index += 1
                    if index >= len(argv):
                        raise ApiError(f"{definition['long']} wymaga wartości")
                    inline = argv[index]
                values[name] = FlagParser.convert(definition, inline)
            else:
                if inline is not None:
                    raise ApiError(f"{definition['long']} nie przyjmuje wartości")
                values[name] = True
            index += 1
        for definition in [*command.get("flags", []), *command.get("positionals", [])]:
            name = definition["name"]
            if name not in values and "default" in definition:
                values[name] = FlagParser.convert(definition, definition["default"])
            if definition.get("required") and name not in values:
                raise ApiError(f"{command['name']} wymaga {definition.get('long', name)}")
        for group in command.get("exclusive_groups", []):
            selected = sum(bool(values.get(name)) for name in group["members"])
            if not int(group.get("minimum", 0)) <= selected <= int(group.get("maximum", 1)):
                flags = ", ".join("--" + name.replace("_", "-") for name in group["members"])
                raise ApiError(f"Wybierz odpowiednią liczbę flag z: {flags}")
        return values

    @staticmethod
    def convert(definition: dict[str, Any], value: Any) -> Any:
        if value is None:
            return None
        kind = definition.get("type")
        try:
            if kind == "integer":
                return int(value)
            if kind == "number":
                return float(value)
            if kind == "boolean":
                if isinstance(value, bool):
                    return value
                if value in ("true", "false"):
                    return value == "true"
                raise ValueError("expected true or false")
        except (TypeError, ValueError) as exc:
            raise ApiError(f"{definition.get('long', definition['name'])}: wymagana wartość typu {kind}") from exc
        return value
