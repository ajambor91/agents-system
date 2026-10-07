"""Expected installation failures displayed without Python tracebacks."""


class InstallationError(RuntimeError):
    """A validated installation or rollback failure."""
