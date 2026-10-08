"""I/O and JSON decoding errors raised by the manifest reader."""


class ManifestJsonError(ValueError):
    """Manifest contains invalid JSON or invalid text encoding."""


class ManifestReadError(OSError):
    """Manifest could not be read from storage."""
