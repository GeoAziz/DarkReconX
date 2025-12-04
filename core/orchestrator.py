"""core.orchestrator

Unified async provider orchestration engine.

This module coordinates execution of multiple provider modules asynchronously,
manages rate-limiting and retries, and merges results into a unified output.
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Type

from core.logger import get_logger
from core.module import BaseModule

logger = get_logger("orchestrator")


class ScanProfile:
    """Named execution profile with provider subsets."""

    FAST = "fast"
    FULL = "full"
    PRIVACY = "privacy"

    PROFILES = {
        FAST: ["dns", "passive_dns", "whois", "tor_check"],
        FULL: ["all"],  # all registered providers
        PRIVACY: ["tor_check", "dns"],
    }

    @staticmethod
    def get_providers(profile: str) -> List[str]:
        """Get list of provider names for a profile."""
        return ScanProfile.PROFILES.get(profile, ScanProfile.PROFILES[ScanProfile.FULL])


class ProviderRegistry:
    """Central provider registration and lifecycle management."""

    def __init__(self):
        self._providers: Dict[str, Type[BaseModule]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        provider_class: Type[BaseModule],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a provider module."""
        self._providers[name] = provider_class
        self._metadata[name] = metadata or {}
        logger.debug(f"Registered provider: {name}")

    def unregister(self, name: str) -> None:
        """Unregister a provider."""
        if name in self._providers:
            del self._providers[name]
            del self._metadata[name]
            logger.debug(f"Unregistered provider: {name}")

    def get(self, name: str) -> Optional[Type[BaseModule]]:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """List all registered providers with metadata."""
        return {
            name: {
                "class": self._providers[name],
                "metadata": self._metadata.get(name, {}),
            }
            for name in self._providers
        }

    def is_enabled(self, name: str) -> bool:
        """Check if provider is enabled (not disabled in metadata)."""
        meta = self._metadata.get(name, {})
        return not meta.get("disabled", False)


# Global registry instance
_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    return _registry


class AsyncOrchestrator:
    """High-performance async provider execution engine."""

    def __init__(
        self,
        registry: ProviderRegistry,
        max_concurrent: int = 5,
        timeout_per_provider: float = 30.0,
    ):
        """Initialize orchestrator.

        Args:
            registry: Provider registry instance
            max_concurrent: Max concurrent provider tasks
            timeout_per_provider: Timeout per provider in seconds
        """
        self.registry = registry
        self.max_concurrent = max_concurrent
        self.timeout_per_provider = timeout_per_provider
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run_providers(
        self,
        target: str,
        providers: Optional[List[str]] = None,
        profile: str = ScanProfile.FULL,
    ) -> Dict[str, Any]:
        """Execute multiple providers concurrently.

        Args:
            target: Scan target (domain, IP, username, etc.)
            providers: Explicit list of provider names (overrides profile)
            profile: Scan profile name (fast, full, privacy)

        Returns:
            Merged result dict with all provider outputs.
        """
        # Determine which providers to run
        if providers is None:
            providers = ScanProfile.get_providers(profile)

        if "all" in providers:
            providers = list(self.registry._providers.keys())

        # Filter to enabled providers
        providers = [p for p in providers if self.registry.is_enabled(p)]

        logger.info(f"Starting async scan of {target} with {len(providers)} provider(s): {', '.join(providers)}")

        start_time = time.time()
        tasks = [self._run_provider(target, provider_name) for provider_name in providers]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        logger.info(f"Async scan completed in {elapsed:.2f}s")

        # Merge results
        merged = self._merge_results(target, providers, results)
        merged["scan_duration_seconds"] = elapsed
        merged["profile"] = profile

        return merged

    async def _run_provider(self, target: str, provider_name: str) -> Dict[str, Any]:
        """Run a single provider with semaphore control."""
        async with self.semaphore:
            provider_class = self.registry.get(provider_name)
            if provider_class is None:
                logger.warning(f"Provider {provider_name} not found")
                return {"provider": provider_name, "success": False, "error": "Provider not found"}

            try:
                logger.debug(f"Starting provider: {provider_name}")
                start = time.time()

                # Instantiate and run (sync interface for now)
                provider = provider_class()
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: provider.run(target)),
                    timeout=self.timeout_per_provider,
                )

                elapsed = time.time() - start
                logger.debug(f"Provider {provider_name} completed in {elapsed:.2f}s")

                if isinstance(result, dict):
                    # Ensure provider is attributed (support both legacy and new envelope)
                    if "provider" not in result:
                        # Some modules return the standardized envelope with 'module'/'status'/'data'
                        # Map that into a provider key for downstream compatibility.
                        if "module" in result:
                            result.setdefault("provider", provider_name)
                        else:
                            result["provider"] = provider_name

                    # Attach execution time if not present
                    result.setdefault("execution_time_seconds", elapsed)
                    return result
                else:
                    return {
                        "provider": provider_name,
                        "success": False,
                        "error": f"Invalid result type: {type(result).__name__}",
                    }
            except asyncio.TimeoutError:
                logger.warning(f"Provider {provider_name} timed out after {self.timeout_per_provider}s")
                return {
                    "provider": provider_name,
                    "success": False,
                    "error": f"Timeout after {self.timeout_per_provider}s",
                }
            except Exception as e:
                logger.error(f"Provider {provider_name} failed: {e}", exc_info=True)
                return {"provider": provider_name, "success": False, "error": str(e)}

    def _merge_results(self, target: str, providers: List[str], results: List[Any]) -> Dict[str, Any]:
        """Merge provider results into unified output.

        Args:
            target: Original scan target
            providers: List of provider names executed
            results: List of result dicts from providers

        Returns:
            Merged result dict with standardized schema.
        """
        merged = {
            "target": target,
            "providers": providers,
            "success": True,
            "data": {},
            "errors": {},
            "cached_flags": {},
        }

        # Normalize results to list (some might be exceptions)
        normalized_results = []
        for result in results:
            if isinstance(result, Exception):
                normalized_results.append({"success": False, "error": str(result)})
            elif isinstance(result, dict):
                normalized_results.append(result)
            else:
                normalized_results.append({"success": False, "error": f"Unexpected result type: {type(result)}"})

        # Process each provider result accepting both new envelope and legacy dict
        for result in normalized_results:
            if not isinstance(result, dict):
                continue

            # Provider attribution: try 'provider', then standardized 'module', else unknown
            provider = result.get("provider") or result.get("module") or "unknown"

            # Detect standardized envelope (status/data/message)
            if "status" in result:
                success = result.get("status") == "ok"
                data = result.get("data")
                error = result.get("message")
                cached = result.get("cached", False)
            else:
                # Legacy shape
                success = result.get("success", False)
                data = result.get("data")
                error = result.get("error")
                cached = result.get("cached", False)

            if success:
                # Extract data
                if data is not None:
                    merged["data"][provider] = data
                # Track cache hit
                if cached:
                    merged["cached_flags"][provider] = True
            else:
                # Track error
                merged["errors"][provider] = error or "Unknown error"
                merged["success"] = False

        # Overall success only if no errors
        merged["success"] = len(merged["errors"]) == 0

        return merged

    async def run_providers_stream(
        self,
        target: str,
        providers: Optional[List[str]] = None,
        profile: str = ScanProfile.FULL,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator that yields provider results as they complete.

        Yields per-provider result dicts (same shape as _run_provider returns).
        After all providers finish, yields a final merged dict under the key '_final'.
        """
        # Determine which providers to run
        if providers is None:
            providers = ScanProfile.get_providers(profile)

        if "all" in providers:
            providers = list(self.registry._providers.keys())

        # Filter to enabled providers
        providers = [p for p in providers if self.registry.is_enabled(p)]

        logger.info(f"Starting async scan stream of {target} with {len(providers)} provider(s): {', '.join(providers)}")

        start_time = time.time()

        tasks = {asyncio.create_task(self._run_provider(target, provider_name)): provider_name for provider_name in providers}

        results = []
        for fut in asyncio.as_completed(list(tasks.keys())):
            res = await fut
            results.append(res)
            # yield individual provider result
            yield res

        elapsed = time.time() - start_time
        logger.info(f"Async scan stream completed in {elapsed:.2f}s")

        merged = self._merge_results(target, providers, results)
        merged["scan_duration_seconds"] = elapsed
        merged["profile"] = profile

        # Final envelope to signal completion
        yield {"_final": True, "merged": merged}


async def run_scan(
    target: str,
    profile: str = ScanProfile.FULL,
    max_concurrent: int = 5,
    timeout_per_provider: float = 30.0,
) -> Dict[str, Any]:
    """Convenience function to run a full async scan.

    Args:
        target: Scan target
        profile: Scan profile (fast, full, privacy)
        max_concurrent: Max concurrent providers
        timeout_per_provider: Timeout per provider in seconds

    Returns:
        Merged result dict.
    """
    registry = get_registry()
    orchestrator = AsyncOrchestrator(registry, max_concurrent, timeout_per_provider)
    return await orchestrator.run_providers(target, profile=profile)


async def run_scan_stream(
    target: str,
    profile: str = ScanProfile.FULL,
    max_concurrent: int = 5,
    timeout_per_provider: float = 30.0,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Convenience async generator that yields provider results as they arrive.

    Example usage:
        async for item in run_scan_stream("example.com", profile="fast"):
            if item.get("_final"):
                do_final(item["merged"])
            else:
                handle_provider(item)
    """
    registry = get_registry()
    orchestrator = AsyncOrchestrator(registry, max_concurrent, timeout_per_provider)
    async for item in orchestrator.run_providers_stream(target, profile=profile):
        yield item
