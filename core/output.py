import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable, List, Optional

from rich.console import Console
from rich.table import Table

console = Console()


def print_header(text: str):
    console.rule(f"[bold cyan]{text}[/bold cyan]")


def print_json(obj: Any, pretty: bool = True):
    if pretty:
        console.print_json(json.dumps(obj, default=str))
    else:
        console.print(json.dumps(obj, default=str))


def print_table(rows: Iterable[dict], columns: Optional[List[str]] = None):
    """Print a table given an iterable of dict-like rows.

    If columns is not provided, it will be inferred from the first row.
    """
    rows = list(rows)
    if not rows:
        console.print("[yellow]No rows to display[/yellow]")
        return

    if columns is None:
        # infer columns from first row keys
        first = rows[0]
        if isinstance(first, dict):
            columns = list(first.keys())
        else:
            # fallback: show str()
            console.print("[yellow]Cannot infer columns for table rows[/yellow]")
            for r in rows:
                console.print(r)
            return

    table = Table(show_header=True)
    for col in columns:
        table.add_column(str(col))

    for r in rows:
        vals = [str(r.get(c, "")) if isinstance(r, dict) else str(getattr(r, c, "")) for c in columns]
        table.add_row(*vals)

    console.print(table)


def save_output(path: str, data: Any, *, ensure_dir: bool = True, format: str = "json"):
    """Save output to file in specified format (json, csv).

    Args:
        path: Output file path
        data: Data to save
        ensure_dir: Create directory if not exists
        format: Output format ('json' or 'csv')
    """
    p = Path(path)
    if ensure_dir and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    if format == "csv":
        _save_csv(p, data)
    else:
        _save_json(p, data)

    console.print(f"[green]✓ Saved {format.upper()} output to {p}[/green]")


def _save_json(path: Path, data: Any):
    """Save data as JSON with proper formatting."""
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, default=str, indent=2)


def _save_csv(path: Path, data: Any):
    """Save data as CSV. Works with list of dicts."""
    if isinstance(data, dict):
        # Single record
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        # Fallback to JSON if CSV doesn't make sense
        _save_json(path, data)
        return

    if not records:
        console.print("[yellow]No data to export to CSV[/yellow]")
        return

    # Extract all unique keys from all records
    fieldnames = set()
    for record in records:
        if isinstance(record, dict):
            fieldnames.update(record.keys())
    fieldnames = sorted(list(fieldnames))

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            if isinstance(record, dict):
                writer.writerow(record)
            else:
                writer.writerow({"value": str(record)})


def setup_file_logging(logfile: Optional[str] = None, log_level: int = logging.INFO) -> Optional[logging.FileHandler]:
    """Setup file-based logging for all operations.

    Args:
        logfile: Path to log file. If None, logging is disabled.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        FileHandler if logfile is set, else None
    """
    if not logfile:
        return None

    logpath = Path(logfile)
    logpath.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(logpath, mode="a")
    file_handler.setLevel(log_level)

    # Standard format for log files
    formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    console.print(f"[dim]📝 Logging to: {logpath}[/dim]")
    return file_handler


def standard_response(module: str, data: Any = None, error: Optional[str] = None) -> dict:
    """Return a standardized module response.

    Success shape:
        {"module": "ipinfo", "status": "ok", "data": {...}}

    Error shape:
        {"module": "ipinfo", "status": "error", "message": "..."}
    """
    if error:
        return {"module": module, "status": "error", "message": str(error)}
    return {"module": module, "status": "ok", "data": data}
