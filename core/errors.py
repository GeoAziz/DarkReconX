"""core.errors

Standardized error types for providers and orchestration.
"""


class ProviderError(Exception):
    """Base error for provider-related failures."""

    def __init__(self, provider_id: str, message: str, status_code: int = None):
        """Initialize provider error.

        Args:
            provider_id: Provider identifier
            message: Error message
            status_code: Optional HTTP status code
        """
        self.provider_id = provider_id
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{provider_id}] {message}")


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, provider_id: str, retry_after: int = None):
        super().__init__(provider_id, f"Rate limit exceeded", status_code=429)
        self.retry_after = retry_after


class ProviderTimeoutError(ProviderError):
    """Provider request timed out."""

    def __init__(self, provider_id: str, timeout_seconds: float):
        super().__init__(provider_id, f"Request timed out after {timeout_seconds}s")
        self.timeout_seconds = timeout_seconds


class ProviderAuthError(ProviderError):
    """Provider authentication failed."""

    def __init__(self, provider_id: str, message: str = "Authentication failed"):
        super().__init__(provider_id, message, status_code=401)


class ProviderNotFoundError(ProviderError):
    """Provider not registered."""

    def __init__(self, provider_id: str):
        super().__init__(provider_id, "Provider not found in registry")


class ScanError(Exception):
    """Scan-level error."""

    def __init__(self, target: str, message: str):
        self.target = target
        self.message = message
        super().__init__(f"[{target}] {message}")


class InvalidProfileError(ScanError):
    """Invalid scan profile specified."""

    def __init__(self, profile: str, valid_profiles: list):
        msg = f"Invalid profile '{profile}'. Valid profiles: {', '.join(valid_profiles)}"
        super().__init__("", msg)


class NoProvidersAvailableError(ScanError):
    """No providers available for scan."""

    def __init__(self, target: str, reason: str = ""):
        msg = f"No providers available for scan"
        if reason:
            msg += f": {reason}"
        super().__init__(target, msg)
