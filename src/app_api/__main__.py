"""Thin entrypoint for ``python -m app_api`` and the installed console."""
from app_api.app.console import Console

execute = Console.execute
emit = Console.emit
main = Console.main

if __name__ == "__main__":
    raise SystemExit(main())
