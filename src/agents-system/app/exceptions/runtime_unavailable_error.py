"""Running modules require a responding resident runtime."""
from .api_error import ApiError


class RuntimeUnavailableError(ApiError):
    pass
