"""Shared, side-effect-free services used by Agents System applications."""

from .get_config import APP_CONFIG_PATH, DEV_CONFIG_PATH, get_config

__all__ = (
    "APP_CONFIG_PATH",
    "DEV_CONFIG_PATH",
    "get_config"
)
