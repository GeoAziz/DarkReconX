import importlib
import inspect
import sys
import json
from pathlib import Path
from typing import Optional

import pyfiglet
import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from rich import box

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


def _format_output(data: dict, format_type: str = "pretty") -> None:
    """
    Format and display UnifiedRecord output.
    
    Args:
        data: UnifiedRecord data as dictionary
        format_type: Output format - "json", "pretty", or "min"
    """
    if format_type == "json":
        # Raw JSON output
        console.print(json.dumps(data, indent=2))
    
    elif format_type == "min":
        # Minimal output - just key facts
        console.print(f"Target: {data.get('target', 'N/A')}")
        console.print(f"Type: {data.get('type', 'N/A')}")
        
        # Show resolved IPs if available
        resolved = data.get("resolved", {})
        if resolved.get("ip"):
            console.print(f"IPs: {', '.join(resolved['ip'][:3])}")
        
        # Show risk if available
        risk = data.get("risk", {})
        if risk.get("malicious"):
            console.print(f"[bold red]⚠️  MALICIOUS (Score: {risk.get('score', 'N/A')})[/bold red]")
        
        # Show network location if available
        network = data.get("network", {})
        if network.get("country"):
            location = f"{network.get('city', '')}, {network.get('country', '')}".strip(", ")
            console.print(f"Location: {location}")
    
    elif format_type == "pretty":
        # Rich formatted output using tables and panels
        
        # Header panel
        target = data.get("target", "Unknown")
        target_type = data.get("type", "Unknown")
        source = data.get("source", "Unknown")
        
        header = f"[bold cyan]Target:[/bold cyan] {target}\n"
        header += f"[bold cyan]Type:[/bold cyan] {target_type}\n"
        header += f"[bold cyan]Source:[/bold cyan] {source}"
        
        console.print(Panel(header, title="[bold yellow]Target Information[/bold yellow]", box=box.ROUNDED))
        
        # DNS Resolution table
        resolved = data.get("resolved", {})
        if any(resolved.values()):
            dns_table = Table(title="DNS Resolution", box=box.SIMPLE)
            dns_table.add_column("Record Type", style="cyan")
            dns_table.add_column("Values", style="white")
            
            if resolved.get("ip"):
                dns_table.add_row("A / AAAA", "\n".join(resolved["ip"]))
            if resolved.get("mx"):
                dns_table.add_row("MX", "\n".join(resolved["mx"]))
            if resolved.get("ns"):
                dns_table.add_row("NS", "\n".join(resolved["ns"]))
            if resolved.get("txt"):
                dns_table.add_row("TXT", "\n".join(resolved["txt"][:3]))  # Limit TXT records
            
            console.print(dns_table)
        
        # WHOIS Information table
        whois = data.get("whois", {})
        if any(v for v in whois.values() if v):
            whois_table = Table(title="WHOIS Information", box=box.SIMPLE)
            whois_table.add_column("Field", style="cyan")
            whois_table.add_column("Value", style="white")
            
            if whois.get("registrar"):
                whois_table.add_row("Registrar", whois["registrar"])
            if whois.get("org"):
                whois_table.add_row("Organization", whois["org"])
            if whois.get("country"):
                whois_table.add_row("Country", whois["country"])
            if whois.get("emails"):
                whois_table.add_row("Emails", ", ".join(whois["emails"][:3]))
            if whois.get("created"):
                whois_table.add_row("Created", whois["created"])
            if whois.get("updated"):
                whois_table.add_row("Updated", whois["updated"])
            if whois.get("expires"):
                whois_table.add_row("Expires", whois["expires"])
            
            console.print(whois_table)
        
        # Network Information table
        network = data.get("network", {})
        if any(network.values()):
            net_table = Table(title="Network Information", box=box.SIMPLE)
            net_table.add_column("Field", style="cyan")
            net_table.add_column("Value", style="white")
            
            if network.get("asn"):
                net_table.add_row("ASN", network["asn"])
            if network.get("asn_name"):
                net_table.add_row("ASN Name", network["asn_name"])
            if network.get("isp"):
                net_table.add_row("ISP", network["isp"])
            if network.get("city"):
                net_table.add_row("City", network["city"])
            if network.get("region"):
                net_table.add_row("Region", network["region"])
            if network.get("country"):
                net_table.add_row("Country", network["country"])
            
            console.print(net_table)
        
        # Risk Assessment panel
        risk = data.get("risk", {})
        if risk.get("score") is not None or risk.get("malicious") or risk.get("categories"):
            risk_content = ""
            
            if risk.get("malicious"):
                risk_content += "[bold red]⚠️  MALICIOUS DETECTED[/bold red]\n"
            else:
                risk_content += "[bold green]✓ No malicious activity detected[/bold green]\n"
            
            if risk.get("score") is not None:
                score = risk["score"]
                score_color = "red" if score > 50 else "yellow" if score > 20 else "green"
                risk_content += f"\n[{score_color}]Risk Score: {score}/100[/{score_color}]"
            
            if risk.get("categories"):
                risk_content += f"\n\nCategories: {', '.join(risk['categories'])}"
            
            console.print(Panel(risk_content, title="[bold yellow]Risk Assessment[/bold yellow]", box=box.ROUNDED))
    
    else:
        console.print(f"[red]Unknown format: {format_type}[/red]")


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
                # Ensure r is a string before concatenation
                if isinstance(r, str):
                    fh.write(r + "\n")
                else:
                    fh.write(str(r) + "\n")
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


@app.command("enrich")
def enrich(
    target: str,
    target_type: str = typer.Option("domain", "--type", "-t", help="Target type: domain, ip, or url"),
    providers: str = typer.Option("dns,whois", "--providers", "-p", help="Comma-separated list of providers to query"),
    output_format: str = typer.Option("pretty", "--format", "-f", help="Output format: json, pretty, or min"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save output to file (JSON format)"),
    tor: Optional[bool] = None,
    ctx: typer.Context = None,
):
    """
    Enrich a target using multiple providers with unified output.
    
    This command uses the Day 9 unification layer to combine data from
    multiple providers into a single, consistent format.
    
    Examples:
        python cli/main.py enrich example.com --pretty
        python cli/main.py enrich 8.8.8.8 --type ip --format json
        python cli/main.py enrich example.com --providers dns,whois,virustotal
    """
    # Resolve global use_tor
    global_use_tor = bool((ctx.obj or {}).get("use_tor", False)) if ctx is not None else False
    use_tor = global_use_tor if tor is None else bool(tor)
    
    console.print(f"[cyan]Enriching target:[/cyan] {target}")
    console.print(f"[cyan]Type:[/cyan] {target_type}")
    console.print(f"[cyan]Providers:[/cyan] {providers}")
    console.print()
    
    # Parse providers list
    provider_list = [p.strip() for p in providers.split(",")]
    
    # Collect data from each provider
    providers_data = {}
    
    with console.status("[bold green]Gathering data from providers...") as status:
        for provider in provider_list:
            try:
                status.update(f"[bold green]Querying {provider}...")
                
                if provider == "dns":
                    # Query DNS
                    try:
                        import dns.resolver
                        resolver = dns.resolver.Resolver()
                        
                        dns_data = {}
                        for record_type in ["A", "MX", "NS", "TXT"]:
                            try:
                                    answers = resolver.resolve(target, record_type)
                                    # answers is an Answer object, which is not directly iterable, but answers.rrset is RRset and is iterable
                                    if hasattr(answers, "rrset") and answers.rrset:
                                        rrset = answers.rrset
                                        if record_type == "A":
                                            dns_data["A"] = [rdata.to_text() for rdata in rrset]
                                        elif record_type == "MX":
                                            dns_data["MX"] = [rdata.to_text() for rdata in rrset]
                                        elif record_type == "NS":
                                            dns_data["NS"] = [rdata.to_text() for rdata in rrset]
                                        elif record_type == "TXT":
                                            # TXT records are bytes, decode if needed
                                            txt_records = []
                                            for rdata in rrset:
                                                val = rdata.to_text()
                                                if isinstance(val, bytes):
                                                    val = val.decode(errors="ignore")
                                                txt_records.append(val)
                                            dns_data["TXT"] = txt_records
                            except Exception:
                                pass
                        
                        if dns_data:
                            providers_data["dns"] = dns_data
                    except Exception as e:
                        console.print(f"[yellow]DNS query failed: {e}[/yellow]")
                
                elif provider == "whois":
                    # Query WHOIS
                    try:
                        from modules.whois_lookup.scanner import WhoisModule
                        whois_mod = WhoisModule()
                        # This would need to be adapted to return data instead of printing
                        console.print(f"[yellow]WHOIS integration pending - use whois command directly[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]WHOIS query failed: {e}[/yellow]")
                
                else:
                    console.print(f"[yellow]Provider '{provider}' not yet integrated[/yellow]")
            
            except Exception as e:
                console.print(f"[red]Error querying {provider}: {e}[/red]")
    
    # Unify the data
    if not providers_data:
        console.print("[red]No data collected from providers[/red]")
        raise typer.Exit(1)
    
    try:
        from core.unify import unify_provider_data
        
        unified_record = unify_provider_data(target, target_type, providers_data)
        record_dict = unified_record.to_dict()
        
        # Display output
        _format_output(record_dict, output_format)
        
        # Save if requested
        if save:
            save_path = Path(save)
            if not save_path.is_absolute():
                results_dir = Path(__file__).resolve().parents[1] / "results"
                results_dir.mkdir(exist_ok=True)
                save_path = results_dir / save
            
            with save_path.open("w", encoding="utf-8") as f:
                json.dump(record_dict, f, indent=2)
            
            console.print(f"\n[green]Saved to: {save_path}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error unifying data: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
