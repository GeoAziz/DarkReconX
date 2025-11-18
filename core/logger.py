"""core.logger

Simple pretty-logging utilities using rich (skeleton).
"""

from rich.console import Console

console = Console()

class Logger:
    def __init__(self, name: str = "DarkReconX"):
        self.name = name

    def info(self, msg: str):
        console.print(f"[bold green][INFO][/bold green] {msg}")

    def warn(self, msg: str):
        console.print(f"[bold yellow][WARN][/bold yellow] {msg}")

    def error(self, msg: str):
        console.print(f"[bold red][ERROR][/bold red] {msg}")
