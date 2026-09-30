from __future__ import annotations

import argparse
import json
import os
import pwd
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.commands.base import CommandBase
from app.services.app_comm import AppCommService


class MessageCommand(CommandBase):
    def execute(self, args: argparse.Namespace) -> int:
        sender, history_home = self._identity(args)
        if not sender:
            raise ValueError("Podaj --sender albo ustaw AGENT_NAME")

        receivers = self._receivers(args.receivers)
        content = self._content(args)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "sender": sender,
            "date": timestamp,
            "receivers": receivers,
            "messages": [{"type": args.type, "content": content}],
        }

        if args.verbose:
            print(
                f"[DEBUG] POST {args.app_comm_url}/api/messages "
                f"sender={sender} receivers={','.join(receivers)}",
                file=sys.stderr,
            )

        result = AppCommService(args.app_comm_url, args.timeout).send_message(payload)
        local_record = {
            "id": result.message_id,
            "status": result.status,
            "sender": sender,
            "receivers": receivers,
            "type": args.type,
            "content": content,
            "timestamp": timestamp,
        }
        local_path: Path | None = None
        if not args.no_local_copy:
            try:
                local_path = self._store_local(history_home, sender, local_record)
            except OSError as exc:
                print(
                    f"[WARN] Wiadomość została wysłana, ale nie zapisano "
                    f"kopii lokalnej: {exc}",
                    file=sys.stderr,
                )

        if args.json:
            print(
                json.dumps(
                    {
                        "messageId": result.message_id,
                        "status": result.status,
                        "localCopy": str(local_path) if local_path else None,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"Wysłano wiadomość {result.message_id} do: {', '.join(receivers)}")
            if local_path:
                print(f"Kopia lokalna: {local_path}")
        return 0

    @staticmethod
    def _receivers(values: list[str]) -> list[str]:
        receivers: list[str] = []
        for value in values:
            for receiver in value.split(","):
                normalized = receiver.strip()
                if normalized and normalized not in receivers:
                    receivers.append(normalized)
        if not receivers:
            raise ValueError("Podaj co najmniej jednego odbiorcę przez --receiver")
        return receivers

    @staticmethod
    def _content(args: argparse.Namespace) -> str:
        if args.content is not None:
            content = args.content
        elif args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            raise ValueError("Podaj --content, --content-file albo treść na stdin")
        if not content.strip():
            raise ValueError("Treść wiadomości nie może być pusta")
        return content

    @staticmethod
    def _identity(args: argparse.Namespace) -> tuple[str | None, Path]:
        if args.admin:
            if args.sender:
                raise ValueError("--admin nie może być użyte razem z --sender")
            invoking_user = (
                os.environ.get("SUDO_USER")
                if os.geteuid() == 0
                else pwd.getpwuid(os.getuid()).pw_name
            )
            if not invoking_user or invoking_user == "root":
                invoking_user = pwd.getpwuid(os.getuid()).pw_name
            account = pwd.getpwnam(invoking_user)
            return invoking_user, Path(account.pw_dir)

        sender = args.sender or os.environ.get("AGENT_NAME")
        history_home = Path(
            os.environ.get("AGENT_HOME")
            or os.environ.get("HOME")
            or pwd.getpwuid(os.getuid()).pw_dir
        )
        return sender, history_home

    def _store_local(
        self,
        history_home: Path,
        sender: str,
        record: dict[str, Any],
    ) -> Path:
        path = history_home / ".agents" / sender / "communication.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        records: list[Any] = []
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                records = current if isinstance(current, list) else [current]
            except json.JSONDecodeError:
                damaged = path.with_suffix(".json.invalid")
                path.replace(damaged)
        records.append(record)

        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(records, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return path
