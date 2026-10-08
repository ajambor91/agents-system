"""Read-only wrapper exposing the active Configuration instance."""

from .configuration import Configuration


class ConfigurationWrapper:
    def __init__(self, configuration: Configuration) -> None:
        self._configuration = configuration

    def get_configuration(self) -> Configuration:
        return self._configuration

    def get_configuration_dict(self) -> dict[str, object]:
        """Return the active immutable configuration as JSON-safe values."""
        settings = type(self._configuration)
        return {name: getattr(settings, name) for name in settings.schema()}
