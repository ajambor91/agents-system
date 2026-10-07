"""Validate a manifest using the model selected by its kind."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "manifests"

from .app.manifests_app import ManifestsApp


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m manifests", description="Walidacja manifestu przez model wybrany według kind.")
    parser.add_argument("manifest", type=Path, help="Ścieżka pliku manifestu JSON.")
    args = parser.parse_args(arguments)
    try:
        application = ManifestsApp()
        document = application.load_manifest(args.manifest)
        application.validate_manifest(document)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"valid": True, "kind": document["kind"], "path": str(args.manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
