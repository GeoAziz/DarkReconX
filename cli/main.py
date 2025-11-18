import typer
import pyfiglet
from rich.console import Console
import importlib
import inspect
from pathlib import Path
from typing import Optional
import yaml

console = Console()
app = typer.Typer(invoke_without_command=True)


def _modules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "modules"


def _read_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "default.yml"
    if not cfg_path.exists():
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, tor: Optional[bool] = typer.Option(None, "--tor/--no-tor", help="Enable or disable Tor routing (overrides config)")):
    banner = pyfiglet.figlet_format("DarkReconX")
    console.print(f"[bold red]{banner}[/bold red]")
    console.print("[bold yellow]Dark Web OSINT Recon Framework[/bold yellow]\n")

    # Determine Tor default: CLI flag overrides config/default.yml
    from config.loader import get_config

    cfg = get_config().config
    cfg_tor = bool(cfg.get("tor", {}).get("enabled", False))
    if tor is None:
        use_tor = cfg_tor
    else:
        use_tor = bool(tor)

    # store in context for subcommands to access
    ctx.obj = ctx.obj or {}
    ctx.obj["use_tor"] = use_tor


@app.command("list")
def list_modules():
    """List available modules in the `modules/` folder."""
    modules_path = _modules_dir()
    modules = [p.name for p in modules_path.iterdir() if p.is_dir()]
    console.print("[bold cyan]Available modules:[/bold cyan]")
    for m in sorted(modules):
        console.print(f" - {m}")


def _find_callable(obj):
    """Find a callable `run`-like method on a module or instance."""
    # direct function
    if callable(getattr(obj, "run", None)):
        return getattr(obj, "run")

    # look for common method names
    candidates = [
        "run",
        "crawl",
        "scan",
        "lookup",
        "search",
        "monitor",
        "analyze",
        "track",
        "validate",
        "identify",
        "detect",
        "enumerate",
        "query",
    ]
    for name in candidates:
        if callable(getattr(obj, name, None)):
            return getattr(obj, name)

    return None


@app.command("run")
def run_module(module: str, target: Optional[str] = None):
    """Run a module's stub. Example: `run dark_market_scanner --target item123`"""
    mod_name = module.strip()
    module_path = f"modules.{mod_name}.scanner"
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        console.print(f"[bold red]Failed to import module {module_path}: {e}[/bold red]")
        raise typer.Exit(1)

    # try function at module level
    callable_obj = _find_callable(mod)

    instance = None
    # figure out whether Tor was requested in the global context
    ctx = typer.get_current_context()
    use_tor = bool((ctx.obj or {}).get("use_tor", False))

    if callable_obj is None:
        # look for a class defined in this module and instantiate it
        classes = [
            cls for name, cls in inspect.getmembers(mod, inspect.isclass) if cls.__module__ == module_path
        ]
        if not classes:
            console.print(f"[yellow]No runnable class or function found in {module_path}[/yellow]")
            raise typer.Exit(1)
        cls = classes[0]
        try:
            # if the class supports a use_tor argument, pass the global value
            try:
                sig = inspect.signature(cls.__init__)
                if "use_tor" in sig.parameters:
                    instance = cls(use_tor=use_tor)
                else:
                    instance = cls()
            except Exception:
                instance = cls()
        except Exception as e:
            console.print(f"[red]Failed to instantiate {cls.__name__}: {e}[/red]")
            raise typer.Exit(1)

        callable_obj = _find_callable(instance)

    if callable_obj is None:
        console.print(f"[yellow]No runnable method found for module {module}[/yellow]")
        raise typer.Exit(1)

    # inspect signature to see if it requires an argument
    sig = inspect.signature(callable_obj)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    try:
        # prepare kwargs for call: include 'use_tor' if the callable accepts it
        call_kwargs = {}
        for p in params:
            if p.name == "use_tor":
                call_kwargs["use_tor"] = use_tor
        if not params:
            result = callable_obj()
        else:
            if target is None and len([p for p in params if p.name != "use_tor"]) > 0:
                console.print("[red]This module requires a target argument. Use --target <value>[/red]")
                raise typer.Exit(2)

            # build positional args (target) and pass kwargs
            pos_args = []
            if any(p.name != "use_tor" for p in params):
                pos_args.append(target)
            result = callable_obj(*pos_args, **call_kwargs)
        console.print(f"[green]Module {module} executed. Result: {result}[/green]")
    except NotImplementedError as e:
        console.print(f"[yellow]Module {module} is a placeholder: {e}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error running module {module}: {e}[/red]")


if __name__ == "__main__":
    app()
