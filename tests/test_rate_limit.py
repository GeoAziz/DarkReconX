"""tests/test_rate_limit.py

Tests for rate limiting and retry logic.
"""

import asyncio

import pytest

from core.rate_limit import (
    GlobalRateLimitManager,
    ProviderRateLimiter,
    TokenBucket,
    get_rate_limit_manager,
)


@pytest.mark.asyncio
class TestTokenBucket:
    """Test token bucket rate limiting."""

    async def test_acquire_tokens(self):
        """Test acquiring tokens."""
        bucket = TokenBucket(capacity=10, tokens_per_second=1.0)

        # Should succeed immediately with initial tokens
        await bucket.acquire(5)
        assert bucket.tokens == 5

    async def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, tokens_per_second=10.0)

        # Drain tokens
        await bucket.acquire(10)
        assert bucket.tokens == 0

        # Wait for refill
        await asyncio.sleep(0.2)
        bucket._refill()

        # Should have ~2 tokens (10 tok/s * 0.2s)
        assert bucket.tokens > 1

    async def test_capacity_limit(self):
        """Test capacity is not exceeded."""
        bucket = TokenBucket(capacity=5, tokens_per_second=10.0)

        await asyncio.sleep(0.2)
        bucket._refill()

        # Should not exceed capacity
        assert bucket.tokens <= 5


@pytest.mark.asyncio
class TestProviderRateLimiter:
    """Test per-provider rate limiting."""

    def test_initialization(self):
        """Test limiter initialization."""
        limiter = ProviderRateLimiter(
            "test_provider",
            tokens_per_second=2.0,
            bucket_capacity=10,
            max_retries=3,
        )

        assert limiter.provider_id == "test_provider"
        assert limiter.max_retries == 3

    def test_should_retry_429(self):
        """Test retry on 429 (rate limit)."""
        limiter = ProviderRateLimiter("test", max_retries=3)

        assert limiter.should_retry(429, attempt=0)
        assert limiter.should_retry(429, attempt=1)
        assert limiter.should_retry(429, attempt=2)
        assert not limiter.should_retry(429, attempt=3)  # Max retries exceeded

    def test_should_retry_5xx(self):
        """Test retry on 5xx (server error)."""
        limiter = ProviderRateLimiter("test", max_retries=3)

        assert limiter.should_retry(500, attempt=0)
        assert limiter.should_retry(503, attempt=0)
        assert not limiter.should_retry(400, attempt=0)  # No retry on 4xx

    def test_should_retry_timeout(self):
        """Test retry on timeout (None status)."""
        limiter = ProviderRateLimiter("test", max_retries=3)

        assert limiter.should_retry(None, attempt=0)
        assert limiter.should_retry(None, attempt=1)

    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        limiter = ProviderRateLimiter("test", backoff_factor=2.0)

        assert limiter.backoff_time(0) == 1  # 2^0
        assert limiter.backoff_time(1) == 2  # 2^1
        assert limiter.backoff_time(2) == 4  # 2^2


@pytest.mark.asyncio
class TestGlobalRateLimitManager:
    """Test global rate limit manager."""

    def test_register_provider(self):
        """Test provider registration."""
        manager = GlobalRateLimitManager()
        limiter = manager.register_provider("test", tokens_per_second=5.0)

        assert limiter is not None
        assert limiter.provider_id == "test"

    def test_get_limiter_auto_create(self):
        """Test auto-create limiter on first get."""
        manager = GlobalRateLimitManager()

        # Should auto-create with defaults
        limiter = manager.get_limiter("new_provider")
        assert limiter is not None
        assert limiter.provider_id == "new_provider"

    @pytest.mark.asyncio
    async def test_safe_request_success(self):
        """Test safe request execution."""
        manager = GlobalRateLimitManager()

        # Mock async request function
        async def mock_request():
            return type("Response", (), {"status_code": 200})()

        response = await manager.safe_request("test", mock_request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_safe_request_retry_on_429(self):
        """Test retry on 429 response."""
        manager = GlobalRateLimitManager()
        call_count = 0

        async def mock_request_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return type("Response", (), {"status_code": 429})()
            return type("Response", (), {"status_code": 200})()

        response = await manager.safe_request("test", mock_request_with_retry)
        assert response.status_code == 200
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_safe_request_failure(self):
        """Test request failure after max retries."""
        manager = GlobalRateLimitManager()

        async def mock_request_fail():
            raise ValueError("Request failed")

        with pytest.raises(ValueError):
            await manager.safe_request("test", mock_request_fail)
