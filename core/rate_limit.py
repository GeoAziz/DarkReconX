"""core.rate_limit

Rate limiting and retry logic for safe API provider access.

Provides per-provider token bucket, exponential backoff, and
standardized retry handling for 429/5xx responses.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from core.logger import get_logger

logger = get_logger("rate_limit")


class TokenBucket:
    """Token bucket for rate limiting.

    Allows burst up to `capacity` tokens, refilled at `tokens_per_second` rate.
    """

    def __init__(self, capacity: int, tokens_per_second: float):
        """Initialize token bucket.

        Args:
            capacity: Max tokens in bucket
            tokens_per_second: Refill rate
        """
        self.capacity = capacity
        self.tokens_per_second = tokens_per_second
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking if necessary."""
        async with self._lock:
            while True:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                # Wait for refill
                wait_time = (tokens - self.tokens) / self.tokens_per_second
                await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.tokens_per_second)
        self.last_update = now


class ProviderRateLimiter:
    """Per-provider rate limiting configuration."""

    def __init__(
        self,
        provider_id: str,
        tokens_per_second: float = 1.0,
        bucket_capacity: int = 5,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        """Initialize rate limiter for a provider.

        Args:
            provider_id: Unique provider identifier
            tokens_per_second: Token refill rate
            bucket_capacity: Max tokens in bucket
            max_retries: Max retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.provider_id = provider_id
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.bucket = TokenBucket(bucket_capacity, tokens_per_second)
        self.retry_count = 0

    async def acquire(self) -> None:
        """Acquire rate limit token."""
        await self.bucket.acquire(1)

    def should_retry(self, status_code: Optional[int], attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            status_code: HTTP status code (None if network error)
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise.
        """
        if attempt >= self.max_retries:
            return False

        # Retry on rate limit
        if status_code == 429:
            return True

        # Retry on server errors
        if status_code and 500 <= status_code < 600:
            return True

        # Retry on timeout/connection errors (None status)
        if status_code is None:
            return True

        return False

    def backoff_time(self, attempt: int) -> float:
        """Calculate exponential backoff wait time.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Wait time in seconds.
        """
        return self.backoff_factor ** attempt


class GlobalRateLimitManager:
    """Centralized rate limit manager for all providers."""

    def __init__(self):
        self._limiters: Dict[str, ProviderRateLimiter] = {}

    def register_provider(
        self,
        provider_id: str,
        tokens_per_second: float = 1.0,
        bucket_capacity: int = 5,
        max_retries: int = 3,
    ) -> ProviderRateLimiter:
        """Register a provider with rate limit config.

        Args:
            provider_id: Unique provider identifier
            tokens_per_second: Rate limit (tokens/second)
            bucket_capacity: Burst capacity
            max_retries: Max retry attempts

        Returns:
            ProviderRateLimiter instance.
        """
        limiter = ProviderRateLimiter(
            provider_id, tokens_per_second, bucket_capacity, max_retries
        )
        self._limiters[provider_id] = limiter
        logger.debug(f"Registered rate limit for {provider_id}: {tokens_per_second} tok/s")
        return limiter

    def get_limiter(self, provider_id: str) -> Optional[ProviderRateLimiter]:
        """Get rate limiter for provider."""
        if provider_id not in self._limiters:
            # Auto-create with defaults
            return self.register_provider(provider_id)
        return self._limiters[provider_id]

    async def safe_request(
        self,
        provider_id: str,
        request_func,
        *args,
        **kwargs,
    ) -> Any:
        """Execute request with rate limiting and retry logic.

        Args:
            provider_id: Provider identifier
            request_func: Async request function to call
            *args: Args to pass to request_func
            **kwargs: Kwargs to pass to request_func

        Returns:
            Response from request_func, or None if all retries failed.
        """
        limiter = self.get_limiter(provider_id)

        for attempt in range(limiter.max_retries + 1):
            try:
                # Acquire rate limit token
                await limiter.acquire()

                # Execute request
                logger.debug(f"[{provider_id}] Attempt {attempt + 1}/{limiter.max_retries + 1}")
                response = await request_func(*args, **kwargs)

                # Check status and decide on retry
                status = getattr(response, "status_code", None) or getattr(response, "status", None)
                if not limiter.should_retry(status, attempt):
                    return response

                if attempt < limiter.max_retries:
                    wait_time = limiter.backoff_time(attempt)
                    logger.warning(
                        f"[{provider_id}] Status {status}, retrying in {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[{provider_id}] Max retries exceeded after status {status}")
                    return response

            except Exception as e:
                logger.debug(f"[{provider_id}] Request failed: {e}")

                if limiter.should_retry(None, attempt) and attempt < limiter.max_retries:
                    wait_time = limiter.backoff_time(attempt)
                    logger.warning(f"[{provider_id}] Error, retrying in {wait_time:.2f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[{provider_id}] Request failed after {attempt + 1} attempt(s): {e}")
                    raise

        return None


# Global rate limit manager instance
_global_manager = GlobalRateLimitManager()


def get_rate_limit_manager() -> GlobalRateLimitManager:
    """Get global rate limit manager."""
    return _global_manager
