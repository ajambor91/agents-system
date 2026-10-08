"""Validate and parse manifest-defined command flags."""

from dataclasses import replace
from typing import Any

from ..exceptions import ApiError
from lib.modules_catalog import Command, Flag


class FlagParser:

    @staticmethod
    def parse(
        command: Command,
        argv: list[str],
    ) -> list[Flag]:

        parsed_flags: list[Flag] = []

        index = 0

        while index < len(argv):
            token = argv[index]

            lookup = token
            inline_value: str | None = None

            if token.startswith("--") and "=" in token:
                lookup, inline_value = token.split("=", 1)

            flag = FlagParser._find_flag(
                command.flags,
                lookup,
            )

            if flag is None:
                if token.startswith("-"):
                    raise ApiError(
                        f"Nieznana flaga dla {command.name}: {lookup}"
                    )

                raise ApiError(
                    f"Nieoczekiwany argument dla {command.name}: {token}"
                )

            if FlagParser._is_already_parsed(
                parsed_flags,
                flag.name,
            ):
                raise ApiError(
                    f"Flaga {FlagParser._display_name(flag)} "
                    "została podana więcej niż raz"
                )

            if flag.takes_value:
                if inline_value is None:
                    index += 1

                    if index >= len(argv):
                        raise ApiError(
                            f"{FlagParser._display_name(flag)} "
                            "wymaga wartości"
                        )

                    inline_value = argv[index]

                value = FlagParser.convert(
                    flag,
                    inline_value,
                )

            else:
                if inline_value is not None:
                    raise ApiError(
                        f"{FlagParser._display_name(flag)} "
                        "nie przyjmuje wartości"
                    )

                value = True

            parsed_flags.append(
                replace(
                    flag,
                    value=value,
                )
            )

            index += 1

        FlagParser._apply_defaults(
            command,
            parsed_flags,
        )

        FlagParser._validate_required(
            command,
            parsed_flags,
        )

        return parsed_flags

    @staticmethod
    def _find_flag(
        flags: list[Flag],
        token: str,
    ) -> Flag | None:

        for flag in flags:
            if token == flag.short:
                return flag

            if token == flag.long:
                return flag

            if token in flag.aliases:
                return flag

        return None

    @staticmethod
    def _is_already_parsed(
        flags: list[Flag],
        name: str,
    ) -> bool:

        return any(
            flag.name == name
            for flag in flags
        )

    @staticmethod
    def _apply_defaults(
        command: Command,
        parsed_flags: list[Flag],
    ) -> None:

        parsed_names = {
            flag.name
            for flag in parsed_flags
        }

        for flag in command.flags:
            if flag.name in parsed_names:
                continue

            if flag.default is None:
                continue

            parsed_flags.append(
                replace(
                    flag,
                    value=FlagParser.convert(
                        flag,
                        flag.default,
                    ),
                )
            )

    @staticmethod
    def _validate_required(
        command: Command,
        parsed_flags: list[Flag],
    ) -> None:

        parsed_names = {
            flag.name
            for flag in parsed_flags
        }

        for flag in command.flags:
            if not flag.required:
                continue

            if flag.name in parsed_names:
                continue

            raise ApiError(
                f"{command.name} wymaga "
                f"{FlagParser._display_name(flag)}"
            )

    @staticmethod
    def _display_name(flag: Flag) -> str:
        if flag.long:
            return flag.long

        if flag.short:
            return flag.short

        if flag.aliases:
            return flag.aliases[0]

        return flag.name

    @staticmethod
    def convert(
        flag: Flag,
        value: Any,
    ) -> Any:

        if value is None:
            return None

        try:
            if flag.type == "integer":
                return int(value)

            if flag.type == "number":
                return float(value)

            if flag.type == "boolean":
                if isinstance(value, bool):
                    return value

                if value == "true":
                    return True

                if value == "false":
                    return False

                raise ValueError(
                    "expected true or false"
                )

        except (TypeError, ValueError) as exc:
            raise ApiError(
                f"{FlagParser._display_name(flag)}: "
                f"wymagana wartość typu {flag.type}"
            ) from exc

        return value
