"""Stress test for DarkReconX — async verification, caching, and performance analysis."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from core.logger import get_logger
from engine.pipeline import run_pipeline_for_targets

logger = get_logger("stress_test")


class PerformanceMonitor:
    """Monitor performance metrics during stress tests."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time: Optional[float] = None
        self.start_memory: Optional[float] = None
        self.metrics = {
            "duration": 0,
            "memory_peak": 0,
            "memory_avg": 0,
            "cpu_percent": 0,
        }

    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Monitor started. Initial memory: {self.start_memory:.1f} MB")

    def end(self):
        """End monitoring and collect metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        self.metrics = {
            "duration_seconds": round(end_time - (self.start_time or 0), 2),
            "memory_start_mb": round(self.start_memory or 0, 2),
            "memory_end_mb": round(end_memory, 2),
            "memory_delta_mb": round(end_memory - (self.start_memory or 0), 2),
            "cpu_percent": self.process.cpu_percent(interval=0.1),
        }

        return self.metrics


async def stress_test_pipeline(
    targets: List[str],
    num_iterations: int = 3,
    verify_http: bool = True,
    outdir: str = "results/stress_test",
) -> Dict[str, Any]:
    """Run pipeline stress test with multiple targets and iterations."""

    logger.info(f"Starting stress test: {len(targets)} targets × {num_iterations} iterations")

    monitor = PerformanceMonitor()
    monitor.start()

    all_results = []
    cache_stats = {
        "total_calls": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }

    for iteration in range(num_iterations):
        logger.info(f"Iteration {iteration + 1}/{num_iterations}")

        try:
            result = await run_pipeline_for_targets(
                targets,
                profile="full",
                verify_http=verify_http,
                outdir=outdir,
                generate_html=False,  # Skip HTML generation for speed
            )
            all_results.append(result)

            # Collect cache stats from summary
            for target_data in result.get("targets", {}).values():
                cache_stats["total_calls"] += 1
                if target_data.get("cached"):
                    cache_stats["cache_hits"] += 1
                else:
                    cache_stats["cache_misses"] += 1

        except Exception as e:
            logger.error(f"Iteration {iteration + 1} failed: {e}")

    metrics = monitor.end()

    # Compile results
    stress_results = {
        "test_config": {
            "targets_count": len(targets),
            "iterations": num_iterations,
            "verify_http": verify_http,
        },
        "performance": metrics,
        "cache_stats": cache_stats,
        "cache_hit_rate": (
            round(cache_stats["cache_hits"] / cache_stats["total_calls"] * 100, 2) if cache_stats["total_calls"] > 0 else 0
        ),
        "avg_time_per_target": round(metrics["duration_seconds"] / (len(targets) * num_iterations), 2),
        "iterations_summary": [
            {
                "iteration": i + 1,
                "targets_scanned": len(r.get("targets", {})),
                "successful": sum(1 for v in r.get("targets", {}).values() if v.get("success")),
            }
            for i, r in enumerate(all_results)
        ],
    }

    return stress_results


def stress_test_caching(
    targets: List[str],
    num_runs: int = 3,
) -> Dict[str, Any]:
    """Test caching effectiveness with repeated queries."""
    import os

    logger.info(f"Cache stress test: {len(targets)} targets × {num_runs} runs")

    monitor = PerformanceMonitor()
    monitor.start()

    results = []

    for run in range(num_runs):
        run_start = time.time()
        logger.info(f"Cache run {run + 1}/{num_runs}")

        # First pass: populate cache
        if run == 0:
            os.environ.pop("DARKRECONX_NO_CACHE", None)
            logger.info("Populating cache...")
        else:
            # Subsequent runs should hit cache
            logger.info("Running with cache...")

        try:
            result = asyncio.run(
                run_pipeline_for_targets(
                    targets,
                    profile="full",
                    verify_http=False,  # Skip HTTP verification for speed
                    outdir="results/cache_test",
                    generate_html=False,
                )
            )

            run_time = time.time() - run_start

            results.append(
                {
                    "run": run + 1,
                    "duration": round(run_time, 2),
                    "targets_scanned": len(result.get("targets", {})),
                }
            )

        except Exception as e:
            logger.error(f"Cache run {run + 1} failed: {e}")

    metrics = monitor.end()

    cache_test_results = {
        "test_type": "cache_effectiveness",
        "targets": targets,
        "num_runs": num_runs,
        "performance": metrics,
        "runs_summary": results,
        "speedup_factor": round(results[0]["duration"] / results[-1]["duration"], 2) if len(results) > 1 else 1.0,
    }

    return cache_test_results


def print_stress_report(results: Dict[str, Any]) -> None:
    """Print a formatted stress test report."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    console.print("\n" + "=" * 70)
    console.print("[bold cyan]DarkReconX Stress Test Report[/bold cyan]")
    console.print("=" * 70 + "\n")

    # Performance summary
    perf = results.get("performance", {})
    console.print(
        Panel(
            f"[bold]Performance Metrics[/bold]\n"
            f"Duration: {perf.get('duration_seconds', 'N/A')}s\n"
            f"Memory Start: {perf.get('memory_start_mb', 'N/A')} MB\n"
            f"Memory End: {perf.get('memory_end_mb', 'N/A')} MB\n"
            f"Memory Delta: {perf.get('memory_delta_mb', 'N/A')} MB\n"
            f"CPU Usage: {perf.get('cpu_percent', 'N/A')}%",
            title="Performance",
        )
    )

    # Cache stats
    cache = results.get("cache_stats", {})
    console.print(
        Panel(
            f"[bold]Cache Statistics[/bold]\n"
            f"Total Calls: {cache.get('total_calls', 'N/A')}\n"
            f"Cache Hits: {cache.get('cache_hits', 'N/A')}\n"
            f"Cache Misses: {cache.get('cache_misses', 'N/A')}\n"
            f"Hit Rate: {results.get('cache_hit_rate', 'N/A')}%",
            title="Caching",
        )
    )

    # Iteration summary
    if "iterations_summary" in results:
        table = Table(title="Iteration Summary")
        table.add_column("Iteration", style="cyan")
        table.add_column("Targets", style="magenta")
        table.add_column("Successful", style="green")

        for summary in results["iterations_summary"]:
            table.add_row(
                str(summary["iteration"]),
                str(summary["targets_scanned"]),
                str(summary["successful"]),
            )

        console.print(table)

    console.print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Example: Run stress test
    test_targets = ["example.com", "google.com", "github.com"]

    results = asyncio.run(
        stress_test_pipeline(
            test_targets,
            num_iterations=2,
            verify_http=False,
        )
    )

    print_stress_report(results)

    # Save results
    results_path = Path("results/stress_test/report.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Stress test report saved to {results_path}")
