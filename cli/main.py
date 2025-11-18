import typer
import pyfiglet
from rich.console import Console

console = Console()
app = typer.Typer()

@app.callback()
def main():
    banner = pyfiglet.figlet_format("DarkReconX")
    console.print(f"[bold red]{banner}[/bold red]")
    console.print("[bold yellow]Dark Web OSINT Recon Framework[/bold yellow]\n")

if __name__ == "__main__":
    app()
