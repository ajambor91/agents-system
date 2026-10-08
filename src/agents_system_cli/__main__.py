"""Thin entrypoint for ``python -m agents_system_cli`` and the installed console."""
from .app import Console

execute = Console.execute
emit = Console.emit
main = Console.main

if __name__ == "__main__":
    raise SystemExit(main())
