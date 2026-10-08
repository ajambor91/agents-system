"""Application factory loaded by Agents System and its local CLI adapter."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "agents_manager"

from .app.application import AgentsApplication
from lib.configuration import Configuration
from lib.manifests_loader import ManifestsLoader
from manifests import ManifestValidator
from lib.logging_config import configure_logging

MODULE_NAME = 'agents_manager'
def get_main_app(configuration: Configuration) -> AgentsApplication:
    configure_logging("agents-manager")
    path = f"{type(configuration).MODULES_DIR}/{MODULE_NAME}/resources/{MODULE_NAME}.module.json"

    manifests = ManifestsLoader.load_manifest(path)
    if ManifestValidator.validate(manifests):
        return AgentsApplication(configuration, manifests)
    raise SystemExit()
