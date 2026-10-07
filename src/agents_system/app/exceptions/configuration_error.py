"""Expected Agents System application error."""
from .api_error import ApiError

class ConfigurationError(ApiError):
    """Invalid or unavailable environment configuration."""
