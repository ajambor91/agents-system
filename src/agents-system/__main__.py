"""Thin module entrypoint for the installed Agents System package."""
from .app.console import Console

execute = Console.execute
emit = Console.emit
main = Console.main

if __name__ == "__main__":
    raise SystemExit(main())
