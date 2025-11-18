import json
from typing import Any, Iterable, List
from rich.console import Console
from rich.table import Table
from pathlib import Path

console = Console()


def print_header(text: str):
    console.rule(f"[bold cyan]{text}[/bold cyan]")


def print_json(obj: Any, pretty: bool = True):
    if pretty:
        console.print_json(json.dumps(obj, default=str))
    else:
        console.print(json.dumps(obj, default=str))


def print_table(rows: Iterable[dict], columns: List[str] = None):
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


def save_output(path: str, data: Any, *, ensure_dir: bool = True):
    p = Path(path)
    if ensure_dir and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    # write JSON representation by default
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, default=str, indent=2)

    console.print(f"[green]Saved output to {p}[/green]")
