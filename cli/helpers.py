"""CLI helpers for DarkReconX — progress, logging, and formatting utilities."""

import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

console = Console()
T = TypeVar("T")


def setup_rich_logging(level: str = "INFO") -> logging.Logger:
    """Set up Rich-based logging with color-coded output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add Rich handler with formatting
    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_level=True,
        show_path=True,
    )
    handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    return root_logger


def print_header(text: str, style: str = "bold cyan") -> None:
    """Print a formatted header."""
    console.print(f"\n[{style}]{'='*60}[/{style}]")
    console.print(f"[{style}]{text:^60}[/{style}]")
    console.print(f"[{style}]{'='*60}[/{style}]\n")


def print_success(text: str) -> None:
    """Print success message in green."""
    console.print(f"[green]✓ {text}[/green]")


def print_warning(text: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[yellow]⚠ {text}[/yellow]")


def print_error(text: str) -> None:
    """Print error message in red."""
    console.print(f"[red]✗ {text}[/red]")


def print_info(text: str) -> None:
    """Print info message in blue."""
    console.print(f"[blue]ℹ {text}[/blue]")


@contextmanager
def progress_bar(total: int, description: str = "Processing"):
    """Context manager for a progress bar."""
    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(description, total=total)

        class ProgressWrapper:
            def update(self, advance: int = 1):
                progress.update(task, advance=advance)

            def set_description(self, new_desc: str):
                progress.update(task, description=new_desc)

        yield ProgressWrapper()


@contextmanager
def spinner(text: str = "Loading"):
    """Context manager for a spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(text, total=None)
        yield


async def async_with_progress(
    coro_list: list, description: str = "Processing", callback: Optional[Callable[[Any], None]] = None
) -> list:
    """Execute a list of coroutines with progress tracking."""
    import asyncio

    results = []
    with progress_bar(len(coro_list), description) as pbar:
        for coro in asyncio.as_completed(coro_list):
            result = await coro
            results.append(result)
            if callback:
                callback(result)
            pbar.update()

    return results


def print_table_results(data: list[dict], title: str = "Results") -> None:
    """Print results as a formatted table."""
    from rich.table import Table

    if not data:
        console.print("[yellow]No results to display[/yellow]")
        return

    table = Table(title=title)

    # Add columns based on first row
    for key in data[0].keys():
        table.add_column(key, style="cyan")

    # Add rows
    for row in data:
        table.add_row(*[str(v) for v in row.values()])

    console.print(table)
