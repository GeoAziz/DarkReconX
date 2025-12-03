"""core.profiler

Performance profiling and benchmarking utilities.
"""

import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from core.logger import get_logger

logger = get_logger("profiler")


class PerformanceMetrics:
    """Track performance metrics for a scan."""

    def __init__(self, target: str):
        self.target = target
        self.start_time = time.time()
        self.provider_metrics: Dict[str, Dict[str, Any]] = {}
        self.checkpoints: List[tuple] = []

    def record_provider(
        self,
        provider_name: str,
        duration_seconds: float,
        success: bool,
        cached: bool = False,
    ) -> None:
        """Record metrics for a provider execution.

        Args:
            provider_name: Name of provider
            duration_seconds: Execution time in seconds
            success: Whether provider succeeded
            cached: Whether result was cached
        """
        self.provider_metrics[provider_name] = {
            "duration_seconds": duration_seconds,
            "success": success,
            "cached": cached,
        }

    def add_checkpoint(self, name: str) -> None:
        """Add a timing checkpoint."""
        elapsed = time.time() - self.start_time
        self.checkpoints.append((name, elapsed))

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_duration = time.time() - self.start_time

        # Sort providers by duration
        sorted_providers = sorted(
            self.provider_metrics.items(),
            key=lambda x: x[1]["duration_seconds"],
            reverse=True,
        )

        # Calculate stats
        successful = sum(1 for m in self.provider_metrics.values() if m["success"])
        cached = sum(1 for m in self.provider_metrics.values() if m["cached"])
        total_provider_time = sum(
            m["duration_seconds"] for m in self.provider_metrics.values()
        )

        return {
            "target": self.target,
            "total_duration_seconds": total_duration,
            "total_provider_time_seconds": total_provider_time,
            "overhead_seconds": total_duration - total_provider_time,
            "providers_executed": len(self.provider_metrics),
            "providers_successful": successful,
            "providers_failed": len(self.provider_metrics) - successful,
            "cached_results": cached,
            "provider_breakdown": [
                {
                    "provider": name,
                    "duration_seconds": metrics["duration_seconds"],
                    "success": metrics["success"],
                    "cached": metrics["cached"],
                }
                for name, metrics in sorted_providers
            ],
        }

    def format_summary(self) -> str:
        """Get formatted performance summary string."""
        summary = self.get_summary()

        lines = [
            f"Performance Summary for {summary['target']}",
            f"Total scan time: {summary['total_duration_seconds']:.2f}s",
            f"Provider time: {summary['total_provider_time_seconds']:.2f}s",
            f"Overhead: {summary['overhead_seconds']:.2f}s",
            f"Providers: {summary['providers_successful']} success, {summary['providers_failed']} failed",
            f"Cached: {summary['cached_results']} results",
            "",
            "Provider Breakdown:",
        ]

        for provider in summary["provider_breakdown"]:
            status = "✓" if provider["success"] else "✗"
            cached_flag = " (cached)" if provider["cached"] else ""
            lines.append(
                f"  {status} {provider['provider']}: {provider['duration_seconds']:.3f}s{cached_flag}"
            )

        return "\n".join(lines)


@contextmanager
def time_block(name: str):
    """Context manager to time a code block.

    Usage:
        with time_block("fetch_data"):
            # code to time
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.debug(f"{name}: {elapsed:.3f}s")


def benchmark_scan(target: str, providers: List[str]) -> Dict[str, Any]:
    """Quick benchmark helper for scan performance.

    Args:
        target: Scan target
        providers: List of providers to benchmark

    Returns:
        Benchmark results dict.
    """
    metrics = PerformanceMetrics(target)

    # Placeholder for actual scan execution
    for provider in providers:
        metrics.record_provider(
            provider,
            duration_seconds=0.1,  # Mock timing
            success=True,
            cached=False,
        )

    return metrics.get_summary()
