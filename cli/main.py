import importlib
import inspect
import sys
from pathlib import Path
from typing import Optional

import pyfiglet
import typer
import yaml
from rich.console import Console

# Ensure project root is on sys.path so `import config` and other top-level
# packages work when running this file directly (python cli/main.py).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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
def main(
    ctx: typer.Context,
    tor: Optional[bool] = typer.Option(None, "--tor/--no-tor", help="Enable or disable Tor routing (overrides config)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose exception output"),
):
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
    ctx.obj["verbose"] = bool(verbose)


@app.command("list")
def list_modules():
    """List available modules discovered by the framework."""
    try:
        from core.loader import discover_modules

        mods = discover_modules()
        console.print("[bold cyan]Available modules:[/bold cyan]")
        for name, cls in sorted(mods.items()):
            desc = getattr(cls, "description", "")
            console.print(f" - [bold]{name}[/bold] - {desc}")
        return
    except Exception:
        # fallback to naive listing
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
def run_module(module: str, target: Optional[str] = None, ctx: typer.Context = None):
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
    # figure out whether Tor and verbose were requested in the global context
    # support receiving the Typer context (injected by Typer when present)
    use_tor = bool((ctx.obj or {}).get("use_tor", False)) if ctx is not None else False
    verbose_flag = bool((ctx.obj or {}).get("verbose", False)) if ctx is not None else False

    if callable_obj is None:
        # look for a class defined in this module and instantiate it
        classes = [cls for name, cls in inspect.getmembers(mod, inspect.isclass) if cls.__module__ == module_path]
        if not classes:
            console.print(f"[yellow]No runnable class or function found in {module_path}[/yellow]")
            raise typer.Exit(1)
        cls = classes[0]
        try:
            # if the class supports a use_tor argument, pass the global value
            try:
                sig = inspect.signature(cls.__init__)
                if "use_tor" in sig.parameters or "verbose" in sig.parameters:
                    # prefer to pass both if the class accepts them
                    kwargs = {}
                    if "use_tor" in sig.parameters:
                        kwargs["use_tor"] = use_tor
                    if "verbose" in sig.parameters:
                        kwargs["verbose"] = verbose_flag
                    instance = cls(**kwargs)
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


@app.command("whois")
def whois(domain: str, tor: Optional[bool] = None, output: Optional[str] = None, ctx: typer.Context = None):
    """WHOIS Lookup Tool"""
    # resolve use_tor from global context if CLI flag not provided
    global_use_tor = bool((ctx.obj or {}).get("use_tor", False)) if ctx is not None else False
    use_tor = global_use_tor if tor is None else bool(tor)

    try:
        from modules.whois_lookup.scanner import WhoisModule
    except Exception as e:
        console.print(f"[red]Failed to import WhoisModule: {e}[/red]")
        raise typer.Exit(1)

    mod = WhoisModule()
    mod.run(domain, use_tor=use_tor, output=output)


@app.command("subfinder")
def subfinder(
    domain: str,
    wordlist: Optional[str] = None,
    tor: Optional[bool] = None,
    workers: Optional[int] = typer.Option(None, "--workers", help="Override number of concurrent workers"),
    verify_http: bool = typer.Option(
        False, "--verify-http", help="Perform HEAD requests to discovered subdomains (respects --tor)"
    ),
    verify_timeout: int = typer.Option(10, "--verify-timeout", help="Timeout (seconds) for HEAD verification"),
    verify_retries: int = typer.Option(2, "--verify-retries", help="Number of retries for HEAD verification"),
    verify_backoff: float = typer.Option(0.5, "--verify-backoff", help="Base backoff (seconds) for HEAD verification"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path under results/ (file)"),
    out_format: str = typer.Option("txt", "--format", "-f", help="Output format: txt|json|csv"),
    api: Optional[str] = typer.Option(None, "--api", help="Optional online API to enrich results (securitytrails|virustotal)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for selected API (optional)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass API cache for enrichment"),
    async_mode: bool = typer.Option(False, "--async", help="Use async resolver prototype (requires dnspython>=2)"),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Force re-fetch and update cache for enrichment"),
    ctx: typer.Context = None,
):
    """Run the Subdomain Finder module.

    Example: python cli/main.py subfinder example.com --tor
    """
    # resolve global use_tor (CLI flag overrides global setting if provided)
    # resolve global use_tor (CLI flag overrides global setting if provided)
    global_use_tor = bool((ctx.obj or {}).get("use_tor", False)) if ctx is not None else False
    use_tor = global_use_tor if tor is None else bool(tor)

    try:
        from modules.subdomain_finder.scanner import SubdomainFinder
    except Exception as e:
        console.print(f"[red]Failed to import SubdomainFinder: {e}[/red]")
        raise typer.Exit(1)

    # choose async vs sync finder
    if async_mode:
        try:
            from modules.subdomain_finder.async_scanner import AsyncSubdomainFinder
        except Exception as e:
            console.print(f"[red]Async mode unavailable: {e}[/red]")
            raise typer.Exit(2)
        finder = AsyncSubdomainFinder(
            domain,
            wordlist=wordlist,
            concurrency=(workers or 100),
            verbose=bool((ctx.obj or {}).get("verbose", False)) if ctx is not None else False,
            verify_http=verify_http,
            http_timeout=float(verify_timeout),
        )
    else:
        finder = SubdomainFinder(
            domain,
            wordlist=wordlist,
            use_tor=use_tor,
            workers=workers,
            verify_http=verify_http,
            verify_timeout=verify_timeout,
            verify_retries=verify_retries,
            verify_backoff=verify_backoff,
            verbose=bool((ctx.obj or {}).get("verbose", False)) if ctx is not None else False,
        )
        # set API options if provided
        if api:
            try:
                finder.set_api(api, api_key=api_key)
                # set cache behavior: CLI flag overrides
                if no_cache:
                    finder.set_api_cache(False)
                if refresh_cache:
                    finder.set_api_refresh(True)
                # env var API_CACHE_BYPASS will also be honored by helpers
            except Exception:
                console.print(
                    f"[yellow]Warning: API {api} not available or failed to configure; continuing without API enrichment[/yellow]"
                )

    # run and save outputs according to format
    results = finder.run()
    # ensure results/ exists at project root
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    results_dir = root / "results"
    results_dir.mkdir(exist_ok=True)

    if output:
        out_path = Path(output)
        if not out_path.is_absolute():
            out_path = results_dir / out_path
    else:
        out_path = results_dir / f"subfinder_{domain}.{out_format}"

    # support formats
    if out_format == "txt":
        with out_path.open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(r + "\n")
        console.print(f"[green]Saved results to {out_path}[/green]")
    elif out_format == "json":
        from core.output import save_output

        save_output(str(out_path), results)
    elif out_format == "csv":
        import csv

        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["subdomain"])
            for r in results:
                writer.writerow([r])
        console.print(f"[green]Saved results to {out_path}[/green]")
    else:
        console.print(f"[red]Unsupported format: {out_format}[/red]")


if __name__ == "__main__":
    app()
