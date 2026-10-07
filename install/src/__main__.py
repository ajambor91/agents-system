#!/usr/bin/env python3
"""CLI entrypoint for the standalone installation application."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

# Checkout execution has the same imports as the installed Python packages.
APPLICATION_ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = Path(__file__).resolve().parent.name
if str(APPLICATION_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(APPLICATION_ROOT / "src"))

from .errors import InstallationError
from .installer import Installer
from .rollback import InstallationRollback
from .uninstaller import Uninstaller
from .reinstaller import Reinstaller
from .reconfigure import Reconfigure
from .shared import installer_parser
from .context import set_mode
from .enums import InstallerMode


def install(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    try:
        if not values:
            raise InstallationError("No installer mode was selected")
        try:
            mode = InstallerMode(values[0])
        except ValueError as exc:
            raise InstallationError(f"Unsupported installer mode: {values[0]}") from exc
        set_mode(mode.value)
        implementations = {
            InstallerMode.INSTALL: Installer,
            InstallerMode.ROLLBACK: InstallationRollback,
            InstallerMode.UNINSTALL: Uninstaller,
            InstallerMode.REINSTALL: Reinstaller,
            InstallerMode.RECONFIGURE: Reconfigure,
        }
        application = implementations[mode]()
        if "--help" in values[1:] or "-h" in values[1:]:
            print(application.help(), end="")
            return 0
        arguments = installer_parser(values[1:], mode)
        result = application.execute(arguments)
    except (InstallationError, OSError, ValueError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(install())
