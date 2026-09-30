#!/usr/bin/env python3
"""CLI entrypoint for the standalone installation application."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from install.src.errors import InstallationError  # noqa: E402
from install.src.installer import Installer, install_parser  # noqa: E402
from install.src.rollback import InstallationRollback, rollback_parser  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    try:
        if values and values[0] == "rollback":
            arguments = rollback_parser().parse_args(values[1:])
            result = InstallationRollback().execute(Path(arguments.journal))
        else:
            arguments = install_parser().parse_args(values)
            result = Installer().execute(arguments)
    except InstallationError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
