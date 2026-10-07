"""Load the active app_env.json into the generated Configuration class."""

from __future__ import annotations

import logging

from pathlib import Path

from lib.configuration import Configuration
from lib.json_loader import JsonLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_CONFIG_PATH = PROJECT_ROOT / "resources" / "app_env.json"
APP_CONFIG_PATH = Path("/etc/agents-system/app_env.json")


LOGGER = logging.getLogger(__name__)


def get_config(
    dev_config: bool | None = None,
    path: str | Path | None = None,
) -> Configuration:
    """Create Configuration from a development or installed JSON document.

    ``path`` is honored only for an explicitly enabled development mode.
    With no mode selected, an installed configuration takes precedence and
    the repository resource is used as the development fallback.
    """
    LOGGER.debug('Starting get_config.get_config path=%s', path)
    if dev_config is True:
        source = Path(path).expanduser() if path is not None else DEV_CONFIG_PATH
    elif dev_config is False:
        source = APP_CONFIG_PATH
    else:
        source = APP_CONFIG_PATH if APP_CONFIG_PATH.is_file() else DEV_CONFIG_PATH

    source = source.resolve(strict=False)
    document = JsonLoader.getJsonFileContent(source)
    if not isinstance(document, dict):
        raise ValueError(f"{source}: configuration must be a JSON object")
    variables = document.get("variables")
    if not isinstance(variables, list):
        raise ValueError(f"{source}: variables must be a list")
    configuration = Configuration(variables)
    LOGGER.info("Configuration loaded: path=%s variables=%s", source, len(variables))
    return configuration


__all__ = [
    "APP_CONFIG_PATH",
    "DEV_CONFIG_PATH",
    "get_config",
]
