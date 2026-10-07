"""Thin module entrypoint for the installed Agents System package."""
from .app.application import Application
from lib.configuration import Configuration
from lib.manifests_loader import ManifestsLoader
from manifests import ManifestValidator


from lib.logging_config import configure_logging

MODULE_NAME = 'agents_system'
def get_main_app(config: Configuration) -> Application:
    configure_logging("agents-system")
    path = f"{type(config).MODULES_DIR}/{MODULE_NAME}/resources/{MODULE_NAME}.module.json"
    manifests = ManifestsLoader.load_manifest(path)
    if ManifestValidator.validate(manifests):
        return Application(config, manifests)
    raise SystemExit()

if __name__ == "__main__":
    raise SystemExit(main())
