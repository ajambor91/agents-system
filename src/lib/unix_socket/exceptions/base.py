"""Default base exception."""

class UnixSocketException(Exception):
    """Default library exception extension point."""

    @property
    def code(self) -> str:
        raise NotImplementedError("UnixSocketException.code is not implemented")

