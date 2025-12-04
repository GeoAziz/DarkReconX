"""tests/test_orchestrator.py

Tests for async orchestration engine and provider registry.
"""

import asyncio

import pytest

from core.errors import ProviderNotFoundError
from core.module import BaseModule
from core.orchestrator import AsyncOrchestrator, ProviderRegistry, ScanProfile, get_registry


class MockProvider(BaseModule):
    """Mock provider for testing."""

    name = "mock"
    description = "Mock provider for tests"

    def __init__(self, delay: float = 0.01, should_fail: bool = False):
        super().__init__()
        self.delay = delay
        self.should_fail = should_fail

    def run(self, target: str):
        # Simulate delay
        import time

        time.sleep(self.delay)

        if self.should_fail:
            return {"success": False, "error": "Mock failure"}

        return {
            "success": True,
            "target": target,
            "data": {"result": f"mock result for {target}"},
        }


class TestProviderRegistry:
    """Test provider registry."""

    def test_register_provider(self):
        """Test provider registration."""
        registry = ProviderRegistry()
        registry.register("test", MockProvider)
        assert registry.get("test") == MockProvider

    def test_unregister_provider(self):
        """Test provider unregistration."""
        registry = ProviderRegistry()
        registry.register("test", MockProvider)
        registry.unregister("test")
        assert registry.get("test") is None

    def test_list_all_providers(self):
        """Test listing all providers."""
        registry = ProviderRegistry()
        registry.register("mock1", MockProvider)
        registry.register("mock2", MockProvider)
        providers = registry.list_all()
        assert "mock1" in providers
        assert "mock2" in providers

    def test_provider_metadata(self):
        """Test provider metadata."""
        registry = ProviderRegistry()
        meta = {"api_key": "test", "rate_limit": 10}
        registry.register("test", MockProvider, metadata=meta)
        providers = registry.list_all()
        assert providers["test"]["metadata"] == meta

    def test_disable_provider(self):
        """Test disabling a provider."""
        registry = ProviderRegistry()
        registry.register("test", MockProvider, metadata={"disabled": True})
        assert not registry.is_enabled("test")


class TestScanProfile:
    """Test scan profiles."""

    def test_get_fast_profile(self):
        """Test fast profile providers."""
        providers = ScanProfile.get_providers(ScanProfile.FAST)
        assert "dns" in providers
        assert "whois" in providers

    def test_get_full_profile(self):
        """Test full profile includes all."""
        providers = ScanProfile.get_providers(ScanProfile.FULL)
        assert "all" in providers

    def test_get_privacy_profile(self):
        """Test privacy profile."""
        providers = ScanProfile.get_providers(ScanProfile.PRIVACY)
        assert "tor_check" in providers
        assert "dns" in providers


@pytest.mark.asyncio
class TestAsyncOrchestrator:
    """Test async orchestrator."""

    @pytest.fixture
    def registry(self):
        """Create registry with mock providers."""
        registry = ProviderRegistry()
        registry.register("mock1", MockProvider)
        registry.register("mock2", MockProvider)
        return registry

    async def test_run_single_provider(self, registry):
        """Test running a single provider."""
        orchestrator = AsyncOrchestrator(registry, max_concurrent=2)
        result = await orchestrator.run_providers("example.com", providers=["mock1"])

        assert result["target"] == "example.com"
        assert result["success"]
        assert "mock1" in result["data"]

    async def test_run_multiple_providers_concurrent(self, registry):
        """Test concurrent execution of multiple providers."""
        orchestrator = AsyncOrchestrator(registry, max_concurrent=2)
        result = await orchestrator.run_providers("example.com", providers=["mock1", "mock2"])

        assert result["target"] == "example.com"
        assert "mock1" in result["data"]
        assert "mock2" in result["data"]

    async def test_provider_timeout(self, registry):
        """Test provider timeout handling."""
        registry.register("slow", MockProvider, metadata={})

        # Override MockProvider to return a slow function
        class SlowProvider(MockProvider):
            def run(self, target: str):
                import time

                time.sleep(5)  # Longer than timeout
                return {"success": True}

        registry.register("slow", SlowProvider)

        orchestrator = AsyncOrchestrator(registry, max_concurrent=2, timeout_per_provider=0.1)
        result = await orchestrator.run_providers("example.com", providers=["slow"])

        assert not result["success"]
        assert "slow" in result["errors"]

    async def test_scan_profile(self, registry):
        """Test scan with profile."""
        registry.register("dns", MockProvider)
        registry.register("whois", MockProvider)

        orchestrator = AsyncOrchestrator(registry)
        # Note: profile="fast" would select dns and whois from FAST profile
        result = await orchestrator.run_providers("example.com", profile=ScanProfile.FAST)

        # Fast profile should include enabled providers
        assert "profile" in result
        assert result["profile"] == ScanProfile.FAST

    async def test_merge_results(self, registry):
        """Test result merging."""
        orchestrator = AsyncOrchestrator(registry)

        providers = ["mock1", "mock2"]
        provider_results = [
            {
                "provider": "mock1",
                "success": True,
                "data": {"ip": "1.2.3.4"},
            },
            {
                "provider": "mock2",
                "success": True,
                "data": {"ip": "5.6.7.8"},
            },
        ]

        merged = orchestrator._merge_results("example.com", providers, provider_results)

        assert merged["target"] == "example.com"
        assert merged["success"]
        # Orchestrator stores data by provider name
        assert "mock1" in merged["data"]
        assert "mock2" in merged["data"]

    async def test_error_handling(self, registry):
        """Test error handling in orchestrator."""
        registry.register("failing", MockProvider)

        # Override to fail
        class FailingProvider(MockProvider):
            def run(self, target: str):
                raise ValueError("Test error")

        registry.register("failing", FailingProvider)

        orchestrator = AsyncOrchestrator(registry)
        result = await orchestrator.run_providers("example.com", providers=["failing"])

        assert not result["success"]
        assert "failing" in result["errors"]
