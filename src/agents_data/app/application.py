#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .commands.message import MessageCommand
from shared.configuration import ApplicationEnvironment
from .commands.placeholders import (
    DriveSyncCommand,
    MemoryFindCommand,
    MemoryGetCommand,
    MemoryWriteCommand,
    SyncCommand,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comm-app", description="Narzędzia lokalnego communication_stack"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    message = subparsers.add_parser(
        "messege_send", help="Wyślij wiadomość przez app-comm"
    )
    message.add_argument(
        "-s", "--sender", help="Nadawca; domyślnie zmienna AGENT_NAME"
    )
    message.add_argument(
        "--admin",
        action="store_true",
        help=(
            "Użyj użytkownika wywołującego jako nadawcy i zapisz historię "
            "w jego katalogu domowym; nie łącz z --sender."
        ),
    )
    message.add_argument(
        "-r",
        "--receiver",
        "--receivers",
        dest="receivers",
        action="append",
        required=True,
        metavar="NAME[,NAME...]",
        help="Odbiorca; flagę można powtarzać lub podać listę po przecinku",
    )
    message.add_argument(
        "-t", "--type", choices=("info", "question"), default="info"
    )
    content = message.add_mutually_exclusive_group()
    content.add_argument("-c", "--content", help="Treść wiadomości")
    content.add_argument(
        "--content-file", metavar="PATH", help="Wczytaj treść z pliku UTF-8"
    )
    message.add_argument(
        "--app-comm-url",
        default=None,
        help="Bazowy URL app-comm",
    )
    message.add_argument("--timeout", type=float, default=10.0)
    message.add_argument(
        "--no-local-copy", action="store_true", help="Nie zapisuj kopii w .agents"
    )
    message.add_argument("--json", action="store_true", help="Wypisz wynik jako JSON")
    message.add_argument("-v", "--verbose", action="store_true")
    message.set_defaults(cmd_class=MessageCommand)

    for name, command_class in (
        ("memory_write", MemoryWriteCommand),
        ("memory_get", MemoryGetCommand),
        ("memory_find", MemoryFindCommand),
        ("drive_sync", DriveSyncCommand),
        ("sync", SyncCommand),
    ):
        command = subparsers.add_parser(name)
        command.set_defaults(cmd_class=command_class)
    return parser


def main(argv: list[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[3]
    configuration = ApplicationEnvironment.discover(repository_root)
    parser = build_parser()
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["messege_send"]:
        arguments = ["messege_send", "--help"]
    try:
        args = parser.parse_args(arguments)
        args.configuration = configuration
        if hasattr(args, "app_comm_url"):
            args.app_comm_url = configuration.select(
                "AGENTS_DATA_COMMUNICATION_APP", flag=args.app_comm_url
            )
        return args.cmd_class().execute(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
