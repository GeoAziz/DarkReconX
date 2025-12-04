# --- DAY 12: ATTACK SURFACE RECON CLI ---
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Optional

import pyfiglet
import typer
import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Normalize repeated -v flags (e.g. -v, -vv) into a single --verbose N before Typer/Cli parses
# This avoids Click/Typer incompatibilities with count/is_flag across versions.
def _normalize_argv_verbosity():
    argv = sys.argv[1:]
    count = 0
    explicit_verbose = False
    new_args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        # handle combined -vvv style
        if a.startswith("-") and not a.startswith("--"):
            # strip leading '-' and check if all v's
            rest = a.lstrip("-")
            if rest and all(ch == "v" for ch in rest):
                count += len(rest)
                i += 1
                continue
        if a == "--verbose":
            explicit_verbose = True
            # keep the flag and its possible value
            new_args.append(a)
            # if there's a following token and it doesn't start with '-', treat it as value
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                new_args.append(argv[i + 1])
                i += 2
                continue
            i += 1
            continue
        # treat single -v as count too
        if a == "-v":
            count += 1
            i += 1
            continue

        new_args.append(a)
        i += 1

    if count > 0:
        # export to environment so Typer/Click don't need to parse repeated -v
        os.environ.setdefault("DARKRECONX_VERBOSITY", str(count))
        # rebuild argv without the -v/-vv tokens (keep any explicit --verbose)
        sys.argv = [sys.argv[0]] + new_args


# run normalization early (module import time)
_normalize_argv_verbosity()

# Ensure project root is on sys.path so `import config` and other top-level
# packages work when running this file directly (python cli/main.py).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

console = Console()
app = typer.Typer(invoke_without_command=True)


def _modules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "modules"


@app.command("asr")
def asr(
    targets: str = typer.Option(..., "--targets", help="File with targets (domains, IPs, subdomains)"),
    max_workers: int = typer.Option(50, "--max-workers", help="Max async workers/concurrency"),
    ports: Optional[str] = typer.Option(None, "--ports", help="Port range, e.g. 1-1000"),
    top_ports: Optional[int] = typer.Option(100, "--top-ports", help="Use top N ports (default 100)"),
    safe_mode: bool = typer.Option(True, "--safe-mode", "--no-safe-mode", help="Safe mode: HEAD only, no admin scan"),
    tls_check: bool = typer.Option(True, "--tls-check", "--no-tls-check", help="Enable SSL/TLS inspection"),
    no_banner: bool = typer.Option(False, "--no-banner", help="Disable banner grabbing"),
    out_format: str = typer.Option("json", "--format", help="Output format: json|csv"),
    output: Optional[str] = typer.Option(None, "--output", help="Output file (default: results/asr_summary.json)"),
):
    """
    Attack Surface Recon (ASR) Mapper: async, modular, safe asset mapping.
    """
    import asyncio
    import csv
    import os

    from engine.asr_pipeline import run_asr

    # Load targets
    with open(targets) as f:
        target_list = [line.strip() for line in f if line.strip()]
    # Port selection
    if ports:
        if "-" in ports:
            start, end = map(int, ports.split("-"))
            port_list = list(range(start, end + 1))
        else:
            port_list = [int(p) for p in ports.split(",") if p.strip().isdigit()]
    else:
        # Top ports (conservative default)
        # Example: top 100 TCP ports
        port_list = [
            80,
            443,
            22,
            21,
            25,
            8080,
            3306,
            53,
            110,
            995,
            143,
            993,
            465,
            587,
            8443,
            23,
            3389,
            139,
            445,
            1723,
            111,
            5900,
            1025,
            8888,
            8000,
            8008,
            53,
            554,
            179,
            389,
            636,
            1521,
            5432,
            49152,
            49153,
            49154,
            49155,
            49156,
            49157,
            49158,
            49159,
            49160,
            49161,
            49162,
            49163,
            49164,
            49165,
            49166,
            49167,
            49168,
            49169,
            49170,
            49171,
            49172,
            49173,
            49174,
            49175,
            49176,
            49177,
            49178,
            49179,
            49180,
            49181,
            49182,
            49183,
            49184,
            49185,
            49186,
            49187,
            49188,
            49189,
            49190,
            49191,
            49192,
            49193,
            49194,
            49195,
            49196,
            49197,
            49198,
            49199,
            49200,
            49201,
            49202,
            49203,
            49204,
            49205,
            49206,
            49207,
            49208,
            49209,
            49210,
            49211,
            49212,
            49213,
            49214,
            49215,
        ][:top_ports]

    # Run async ASR pipeline
    results = asyncio.run(
        run_asr(
            target_list, port_list, safe_mode=safe_mode, tls_check=tls_check, banner=not no_banner, concurrency=max_workers
        )
    )

    # Output
    if not output:
        output = "results/asr_summary.json"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    if out_format == "json":
        with open(output, "w") as f:
            import json

            json.dump(results, f, indent=2)
        console.print(f"[green]ASR results saved to {output}[/green]")
    elif out_format == "csv":
        # Flatten and write CSV
        keys = ["target", "ip", "port", "protocol", "service", "banner", "risk", "remediation"]
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                row = {k: r.get(k, "") for k in keys}
                row["risk"] = ",".join(r.get("risk", {}).get("reasons", []))
                row["remediation"] = ",".join(r.get("remediation", []))
                writer.writerow(row)
        console.print(f"[green]ASR CSV results saved to {output}[/green]")
    else:
        console.print(f"[red]Unknown output format: {out_format}[/red]")


def _read_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "default.yml"
    if not cfg_path.exists():
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _format_output(data: dict, format_type: str = "pretty", verbosity: int = 0) -> None:
    """
    Format and display UnifiedRecord output.

    Args:
        data: UnifiedRecord data as dictionary
        format_type: Output format - "json", "pretty", or "min"
    """
    # Prefer a centralized renderer if available (new Day 23 UX)
    try:
        from core import render as _render  # type: ignore

        # Try to determine verbosity from click/typer context if available if not passed
        try:
            import click

            ctx = click.get_current_context(silent=True)
            if verbosity == 0 and ctx is not None and getattr(ctx, "obj", None):
                verbosity = int(ctx.obj.get("verbosity", 0))
        except Exception:
            pass

        _render.render_output(data, format_type=format_type, verbosity=verbosity)
        return
    except Exception:
        # Fall back to built-in formatting for backwards compatibility
        pass

    if format_type == "json":
        console.print(json.dumps(data, indent=2))

    elif format_type == "min":
        console.print(f"Target: {data.get('target', 'N/A')}")
        console.print(f"Type: {data.get('type', 'N/A')}")

        resolved = data.get("resolved", {})
        if resolved.get("ip"):
            console.print(f"IPs: {', '.join(resolved['ip'][:3])}")

        risk = data.get("risk", {})
        if risk.get("malicious"):
            console.print(f"[bold red]⚠️  MALICIOUS (Score: {risk.get('score', 'N/A')})[/bold red]")

        network = data.get("network", {})
        if network.get("country"):
            location = f"{network.get('city', '')}, {network.get('country', '')}".strip(", ")
            console.print(f"Location: {location}")

    elif format_type == "pretty":
        target = data.get("target", "Unknown")
        target_type = data.get("type", "Unknown")
        source = data.get("source", "Unknown")

        header = f"[bold cyan]Target:[/bold cyan] {target}\n"
        header += f"[bold cyan]Type:[/bold cyan] {target_type}\n"
        header += f"[bold cyan]Source:[/bold cyan] {source}"

        console.print(Panel(header, title="[bold yellow]Target Information[/bold yellow]", box=box.ROUNDED))

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
                dns_table.add_row("TXT", "\n".join(resolved["txt"][:3]))

            console.print(dns_table)

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
    tor: bool = typer.Option(False, "--tor", "--no-tor", help="Enable or disable Tor routing (overrides config)"),
    format: str = typer.Option("pretty", "--format", "-f", help="Output format: pretty|json|md"),
    verbose: int = typer.Option(0, "--verbose", help="Increase verbosity (use -v or -vv)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Reduce console output"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache reads and writes"),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Force refresh and update cache"),
):
    # Acquire click/typer Context at runtime to avoid Typer introspection issues
    import click

    click_ctx = click.get_current_context(silent=True)
    if click_ctx is None:

        class _DummyCtx:
            def __init__(self):
                # provide obj attribute to match click.Context interface used by the app
                self.obj = {}

        click_ctx = _DummyCtx()

    ctx = click_ctx
    banner = pyfiglet.figlet_format("DarkReconX")
    # Respect quiet mode
    if not quiet:
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
    # combine verbosity from the CLI option and any -v repetitions normalized into
    # the DARKRECONX_VERBOSITY environment variable (see top-level normalization)
    env_verb = int(os.environ.get("DARKRECONX_VERBOSITY", "0"))
    try:
        cli_verb = int(verbose)
    except Exception:
        cli_verb = 0
    ctx.obj["use_tor"] = use_tor
    ctx.obj["verbosity"] = int(cli_verb or env_verb)
    ctx.obj["format"] = format
    ctx.obj["quiet"] = bool(quiet)
    # cache flags exposed to modules
    ctx.obj["no_cache"] = bool(no_cache)
    ctx.obj["refresh_cache"] = bool(refresh_cache)

    # export environment variables so provider modules can opt-in to read them
    os.environ["DARKRECONX_NO_CACHE"] = "1" if no_cache else "0"
    os.environ["DARKRECONX_REFRESH_CACHE"] = "1" if refresh_cache else "0"


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


@app.command("profiles")
def profiles():
    """List available scan profiles (presets)."""
    try:
        from core.profiles import load_profiles

        profiles = load_profiles()
        if not profiles:
            console.print("[yellow]No profiles found (check config/profiles.yml or profiles.yaml)[/yellow]")
            return

        console.print("[bold cyan]Available profiles:[/bold cyan]")
        for name, cfg in profiles.items():
            # Show a one-line summary if available
            summary = cfg.get("description", "") if isinstance(cfg, dict) else ""
            console.print(f" - [bold]{name}[/bold] {(' - ' + summary) if summary else ''}")
    except Exception as e:
        console.print(f"[red]Failed to load profiles: {e}[/red]")


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
def run_module(module: str, target: Optional[str] = None, ctx=None):
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
    ctx_obj = getattr(ctx, "obj", {}) or {}
    use_tor = bool(ctx_obj.get("use_tor", False))
    verbose_flag = bool(ctx_obj.get("verbose", False))

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

        # Normalize result with standardized response shape
        try:
            from core.output import standard_response, print_json

            resp = standard_response(module, data=result)
            # prefer pretty JSON display
            print_json(resp, pretty=True)
        except Exception:
            console.print(f"[green]Module {module} executed. Result: {result}[/green]")
    except NotImplementedError as e:
        console.print(f"[yellow]Module {module} is a placeholder: {e}[/yellow]")
    except Exception as e:
        try:
            from core.output import standard_response, print_json

            resp = standard_response(module, error=str(e))
            print_json(resp, pretty=True)
        except Exception:
            console.print(f"[red]Error running module {module}: {e}[/red]")


@app.command("whois")
def whois(
    domain: str,
    tor: Optional[bool] = typer.Option(None, "--tor", "--no-tor", help="Enable or disable Tor routing (overrides config)"),
    output: Optional[str] = None,
    ctx=None,
):
    """WHOIS Lookup Tool"""
    # resolve use_tor from global context if CLI flag not provided
    if ctx is None:
        global_use_tor = False
    else:
        # use getattr to safely access 'obj' on an unknown ctx type
        ctx_obj = getattr(ctx, "obj", {}) or {}
        global_use_tor = bool(ctx_obj.get("use_tor", False))
    use_tor = global_use_tor if tor is None else bool(tor)

    try:
        from modules.whois_lookup.scanner import WhoisModule
    except Exception as e:
        console.print(f"[red]Failed to import WhoisModule: {e}[/red]")
        raise typer.Exit(1)

    mod = WhoisModule()
    try:
        # Prefer structured output if the module exposes it
        if callable(getattr(mod, "run_structured", None)):
            result = mod.run_structured(domain, use_tor=use_tor, output=output)
        else:
            result = mod.run(domain, use_tor=use_tor, output=output)
    except Exception as e:
        console.print(f"[red]WHOIS module failed: {e}[/red]")
        raise typer.Exit(1)

    # After retrieval, run fusion to compute confidence and persist profile
    try:
        from core import fusion as _fusion
        from core.profiles import load_metadata, save_metadata, add_module_usage

        sources = {"whois": result.get("whois") if isinstance(result, dict) and "whois" in result else result}
        fused = _fusion.fuse_domain(domain, sources)
        meta = load_metadata(domain) or {}
        meta["confidence"] = fused.get("confidence", 0.0)
        save_metadata(domain, meta)
        add_module_usage(domain, "whois")
    except Exception:
        pass

    # Render output using centralized renderer if available (respect --format / -v)
    ctx_obj = getattr(ctx, "obj", {}) or {}
    output_format = ctx_obj.get("format", "pretty")
    verbosity = int(ctx_obj.get("verbosity", 0))
    _format_output(result if isinstance(result, dict) else {"result": result}, output_format, verbosity)


@app.command("tui")
def tui():
    """Launch the interactive Textual TUI dashboard (Day 22)."""
    try:
        # Import the local tui launcher
        from tui import launch_tui

        launch_tui()
    except Exception as e:
        console.print(f"[red]Failed to launch TUI: {e}[/red]")
        console.print("Ensure `textual` is installed: pip install textual rich")


@app.command("note")
def note(
    target: str = typer.Argument(..., help="Target identifier (domain)"),
    add: Optional[str] = typer.Option(None, "--add", help="Add a note to the target"),
):
    """Add or show analyst notes for a target profile."""
    try:
        from core.profiles import add_note, get_profile_dir

        if add:
            add_note(target, add)
            console.print(f"[green]Note added to profile:{get_profile_dir(target)}[/green]")
        else:
            notes = get_profile_dir(target) / "notes.md"
            if notes.exists():
                console.print(notes.read_text(encoding="utf-8"))
            else:
                console.print("[yellow]No notes found for target[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to write/read notes: {e}[/red]")


@app.command("report")
def report(
    target: str = typer.Argument(..., help="Target identifier (domain)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output HTML path"),
):
    """Generate an HTML intelligence report for a target."""
    try:
        from core.profiles import get_profile_dir, load_metadata
        from core.report import generate_html_report

        profile_dir = get_profile_dir(target)

        # Gather collections
        def _load_json(name):
            p = profile_dir / f"{name}.json"
            if p.exists():
                try:
                    import json

                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    return []
            return []

        profile = {
            "domains": _load_json("domains"),
            "ips": _load_json("ips"),
            "emails": _load_json("emails"),
        }

        meta = load_metadata(target)
        # Attach a simple fused confidence if present
        profile["confidence"] = meta.get("confidence", 0.0)

        if output:
            out = Path(output)
        else:
            out = Path(__file__).resolve().parents[1] / "reports" / f"{target}.html"

        path = generate_html_report(target, profile, out)
        console.print(f"[green]Report generated: {path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to generate report: {e}[/red]")


@app.command("graph")
def graph(
    target: str = typer.Argument(..., help="Target identifier (domain)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output image path (png)"),
):
    """Generate a relationship graph for a target using Graphviz (dot)."""
    try:
        from core.profiles import get_profile_dir
        from core.correlation import correlate_domains_by_ip, detect_shared_asn

        profile_dir = get_profile_dir(target)

        import json

        domains = []
        ips = []
        p_domains = profile_dir / "domains.json"
        p_ips = profile_dir / "ips.json"
        if p_domains.exists():
            domains = json.loads(p_domains.read_text(encoding="utf-8"))
        if p_ips.exists():
            ips = json.loads(p_ips.read_text(encoding="utf-8"))

        # Build a richer dot graph with node types, edge labels and ASN clustering
        def esc(s) -> str:
            # coerce to str and escape double quotes for DOT labels
            return str(s).replace('"', '\\"')

        lines = ["digraph G {", "rankdir=LR;", "compound=true;", 'node [style=filled, fontname="Helvetica"];']

        domain_nodes = []
        ip_nodes = []
        email_nodes = []
        asn_map = {}

        # add domain nodes
        for d in domains:
            if isinstance(d, str):
                name = d
                domain_nodes.append(name)
                lines.append(f'"{esc(name)}" [shape=oval, fillcolor="#E6F0FF", color="#2B6CB0", label="{esc(name)}"];')
            elif isinstance(d, dict):
                name = d.get("domain") or d.get("name")
                domain_nodes.append(name)
                label = esc(name)
                lines.append(f'"{esc(name)}" [shape=oval, fillcolor="#E6F0FF", color="#2B6CB0", label="{label}"];')
                # capture ASN if present
                if d.get("asn"):
                    asn = str(d.get("asn"))
                    asn_map.setdefault(asn, []).append(name)
                # capture associated IPs
                if d.get("ip"):
                    ip_nodes.append(d.get("ip"))

        # add ip nodes
        for ip in ips:
            if isinstance(ip, str) and ip not in ip_nodes:
                ip_nodes.append(ip)
        for ip in sorted(set(ip_nodes)):
            lines.append(f'"{esc(ip)}" [shape=rect, fillcolor="#FFF4E6", color="#D97706", label="{esc(ip)}"];')

        # if domains contained emails or social entries, include them
        # detect emails in domain dicts
        for d in domains:
            if isinstance(d, dict):
                emails = d.get("emails") or d.get("email") or []
                if isinstance(emails, str):
                    emails = [emails]
                for e in emails:
                    email_nodes.append(e)
                    lines.append(f'"{esc(e)}" [shape=note, fillcolor="#ECFCCB", color="#15803D", label="{esc(e)}"];')

        # add ASN cluster subgraphs for visual grouping
        for asn, members in asn_map.items():
            safe_asn = esc(asn).replace(".", "_")
            lines.append(f"subgraph cluster_asn_{safe_asn} {{")
            lines.append(f'  label = "ASN {esc(asn)}";')
            lines.append("  style=filled;")
            lines.append('  color="#F3E8FF";')
            for m in members:
                lines.append(f'  "{esc(m)}";')
            lines.append("}")

        # add edges: domain -> ip (resolves), domain -> email (owner), ip -> asn (if present in domain dicts)
        # domain->ip
        for d in domains:
            if isinstance(d, dict) and d.get("ip"):
                dom = esc(d.get("domain"))
                ip = esc(d.get("ip"))
                lines.append(f'"{dom}" -> "{ip}" [label="resolves", color="#9CA3AF", penwidth=1.2];')

        # domain->email
        for d in domains:
            if isinstance(d, dict):
                name = esc(d.get("domain") or d.get("name"))
                emails = d.get("emails") or d.get("email") or []
                if isinstance(emails, str):
                    emails = [emails]
                for e in emails:
                    lines.append(f'"{name}" -> "{esc(e)}" [label="contact", color="#86EFAC", penwidth=1.0];')

        # shared IP correlations as dashed edges with confidence label from correlation helper
        try:
            profile = {"domains": domains}
            shared = correlate_domains_by_ip(profile)
            for ip, doms, conf in shared:
                for dom in doms:
                    lines.append(f'"{esc(dom)}" -> "{esc(ip)}" [label="shared ({conf})", style=dashed, color="#F59E0B"];')
        except Exception:
            pass

        lines.append("}")

        dot = "\n".join(lines)
        # determine output paths
        if output:
            out = Path(output)
        else:
            out = Path(__file__).resolve().parents[1] / "reports" / f"{target}.png"

        out.parent.mkdir(parents=True, exist_ok=True)

        # Try to render with graphviz if installed (use dynamic import to avoid static import errors)
        try:
            import importlib

            graphviz = importlib.import_module("graphviz")
            g = graphviz.Source(dot)
            g.render(str(out.with_suffix("")), format="png", cleanup=True)
            console.print(f"[green]Graph image generated: {out}[/green]")
        except Exception:
            # fallback: write dot file
            try:
                dot_path = out.with_suffix(".dot")
                dot_path.write_text(dot, encoding="utf-8")
                console.print(f"[yellow]graphviz not available — wrote DOT to {dot_path}[/yellow]")
            except Exception as e:
                console.print(f"[red]Failed to write DOT file: {e}[/red]")

    except Exception as e:
        console.print(f"[red]Failed to generate graph: {e}[/red]")


# --- DAY 11 SUBDOMAIN ENUM ENGINE CLI ---
@app.command("subfinder")
def subfinder(
    domain: str = typer.Argument(..., help="Target domain for subdomain enumeration"),
    wordlist: Optional[str] = typer.Option(None, "--wordlist", "-w", help="Wordlist for brute-force (SecLists)"),
    subs: bool = typer.Option(False, "--subs", help="Passive subdomain enumeration only"),
    subs_only: bool = typer.Option(False, "--subs-only", help="Passive only, skip active/perms/validation"),
    bruteforce: bool = typer.Option(False, "--bruteforce", help="Active brute-force only"),
    perms: bool = typer.Option(False, "--perms", help="Permutation engine only"),
    full_subenum: bool = typer.Option(
        False, "--full-subenum", help="Full subdomain enumeration (passive + active + perms + validation)"
    ),
    vt_api_key: Optional[str] = typer.Option(None, "--vt-api-key", help="VirusTotal API key for passive enum"),
    concurrency: int = typer.Option(200, "--concurrency", help="Max async DNS concurrency"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path (JSON)"),
    ctx=None,
):
    """
    Hybrid Subdomain Enumeration Engine (Passive, Active, Permutations, Validation)
    """
    import asyncio
    import os

    from modules.subdomains.engine import subdomain_enum

    # Determine mode
    if full_subenum:
        mode = "full"
    elif subs_only:
        mode = "subs"
    elif bruteforce:
        mode = "bruteforce"
    elif perms:
        mode = "perms"
    elif subs:
        mode = "subs"
    else:
        mode = "full"

    # Load wordlist if needed
    wl = []
    if wordlist and (mode in ("full", "bruteforce", "perms")):
        if os.path.exists(wordlist):
            with open(wordlist) as f:
                wl = [line.strip() for line in f if line.strip()]
        else:
            console.print(f"[red]Wordlist not found: {wordlist}[/red]")
            raise typer.Exit(1)

    # Run async engine
    result = asyncio.run(
        subdomain_enum(domain, wordlist=wl if wl else None, vt_api_key=vt_api_key, mode=mode, concurrency=concurrency)
    )

    # Output
    if output:
        out_path = Path(output)
        if not out_path.is_absolute():
            out_path = Path(__file__).resolve().parents[1] / "results" / "subdomains" / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Saved results to {out_path}[/green]")
    else:
        # Prefer centralized renderer if available; build a consistent record shape
        record = {
            "target": domain,
            "type": "subdomains",
            "count": result.get("count", 0),
            "subdomains": result.get("subdomains", []),
        }

        # Run fusion and persist confidence
        try:
            from core import fusion as _fusion
            from core.profiles import load_metadata, save_metadata, add_module_usage

            sources = {"local_dns": result}
            fused = _fusion.fuse_domain(domain, sources)
            meta = load_metadata(domain) or {}
            meta["confidence"] = fused.get("confidence", 0.0)
            save_metadata(domain, meta)
            add_module_usage(domain, "subfinder")
        except Exception:
            pass

        # Determine format/verbosity from ctx if provided
        if ctx is not None:
            ctx_obj = getattr(ctx, "obj", {}) or {}
        else:
            ctx_obj = {}
        output_format = ctx_obj.get("format", "pretty")
        verbosity = int(ctx_obj.get("verbosity", 0))

        _format_output(record, output_format, verbosity)


@app.command("enrich")
def enrich(
    target: str,
    target_type: str = typer.Option("domain", "--type", "-t", help="Target type: domain, ip, or url"),
    providers: str = typer.Option("dns,whois", "--providers", "-p", help="Comma-separated list of providers to query"),
    output_format: str = typer.Option("pretty", "--format", "-f", help="Output format: json, pretty, or min"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save output to file (JSON format)"),
    tor: Optional[bool] = typer.Option(None, "--tor", "--no-tor", help="Enable or disable Tor routing (overrides config)"),
    ctx=None,
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

                # Check for required API keys for some providers and skip safely
                if provider in ("virustotal", "vt", "virus_total"):
                    try:
                        from core.keys import check_api_key

                        present, msg = check_api_key("VT_API_KEY")
                        if not present:
                            console.print(f"[yellow]{msg}[/yellow]")
                            continue
                    except Exception:
                        # best-effort: if keys helper fails, continue
                        pass
                if provider in ("ipinfo",):
                    try:
                        from core.keys import check_api_key

                        present, msg = check_api_key("IPINFO_TOKEN")
                        if not present:
                            console.print(f"[yellow]{msg}[/yellow]")
                            continue
                    except Exception:
                        pass

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
                        # This would need to be adapted to return data instead of printing
                        console.print("[yellow]WHOIS integration pending - use whois command directly[/yellow]")
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
        from core import fusion as _fusion
        from core.profiles import load_metadata, save_metadata, add_module_usage

        unified_record = unify_provider_data(target, target_type, providers_data)
        record_dict = unified_record.to_dict()

        # Run fusion to compute confidence and persist into metadata
        try:
            fused = _fusion.fuse_domain(target, providers_data)
            meta = load_metadata(target) or {}
            meta["confidence"] = fused.get("confidence", 0.0)
            save_metadata(target, meta)
            add_module_usage(target, "enrich")
            for p in provider_list:
                add_module_usage(target, f"provider_{p}")
        except Exception:
            # best-effort: fusion should not break the enrich flow
            pass

        # Collect format/verbosity propagated from global callback (if any)
        if ctx is not None:
            ctx_obj = getattr(ctx, "obj", {}) or {}
        else:
            ctx_obj = {}
        output_format = ctx_obj.get("format", output_format)
        verbosity = int(ctx_obj.get("verbosity", 0))

        # Display output
        _format_output(record_dict, output_format, verbosity)

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


@app.command("pipeline")
def pipeline(
    targets: str = typer.Option(..., "--targets", "-t", help="Target file (one per line) or single target"),
    profile: str = typer.Option("full", "--profile", help="Scan profile: fast, full, privacy"),
    verify_http: bool = typer.Option(True, "--verify-http", "--no-verify-http", help="Enable HTTP verification"),
    outdir: Optional[str] = typer.Option(None, "--outdir", help="Output directory (default: results/pipeline)"),
    ctx=None,
):
    """Run the full integrated pipeline for a set of targets.

    The `targets` argument may be a path to a file with one target per line
    or a single domain/IP string.
    """
    try:
        from engine.pipeline import run_pipeline_cli
    except Exception as e:
        console.print(f"[red]Pipeline module not available: {e}[/red]")
        raise typer.Exit(1)

    # Collect flags propagated from global callback
    if ctx is not None:
        ctx_obj = getattr(ctx, "obj", {}) or {}
    else:
        ctx_obj = {}
    no_cache = bool(ctx_obj.get("no_cache", False))
    refresh_cache = bool(ctx_obj.get("refresh_cache", False))

    kwargs = {
        "profile": profile,
        "verify_http": verify_http,
    }
    if outdir:
        kwargs["outdir"] = outdir

    # Export env for providers to pick up if needed
    os.environ["DARKRECONX_NO_CACHE"] = "1" if no_cache else "0"
    os.environ["DARKRECONX_REFRESH_CACHE"] = "1" if refresh_cache else "0"

    console.print(f"[cyan]Starting pipeline for targets: {targets}[/cyan]")
    run_pipeline_cli(targets, **kwargs)
    console.print(f"[green]Pipeline completed. Summary written to {kwargs.get('outdir','results/pipeline')}[/green]")


if __name__ == "__main__":
    try:
        app()
    except TypeError as e:
        # Workaround for Typer/Rich/Click compatibility issues when
        # formatting help text (some versions of click.Param.make_metavar
        # have a different signature). Fall back to Click's plain help.
        msg = str(e)
        if "make_metavar" in msg or "Secondary flag is not valid" in msg:
            # Typer/Rich/Click mismatch when formatting help; print a simple
            # fallback help by scanning this file for @app.command usages.
            try:
                from pathlib import Path

                this = Path(__file__)
                src = this.read_text(encoding="utf-8")
                lines = src.splitlines()

                commands = []
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("@app.command"):
                        # capture decorator argument if present
                        name = None
                        if "(" in line and ")" in line:
                            inside = line[line.find("(") + 1 : line.rfind(")")].strip()
                            if inside:
                                # remove quotes
                                name = inside.strip().strip('"').strip("'")
                        # look ahead for def
                        j = i + 1
                        while j < len(lines) and not lines[j].strip().startswith("def "):
                            j += 1
                        if j < len(lines):
                            def_line = lines[j].strip()
                            # extract function name
                            fn = def_line.split("def ", 1)[1].split("(", 1)[0].strip()
                            cmd_name = name or fn
                            # try to read one-line docstring
                            doc = ""
                            k = j + 1
                            # skip possible decorators or blank lines
                            while k < len(lines) and lines[k].strip() == "":
                                k += 1
                            if k < len(lines) and lines[k].strip().startswith('"""'):
                                doc_line = lines[k].strip().lstrip('"""').strip()
                                doc = doc_line.split("\n", 1)[0]
                            commands.append((cmd_name, doc))
                            i = j
                    i += 1

                # Print a simple help summary
                print("\nUsage: python -m cli.main [OPTIONS] COMMAND [ARGS]...\n")
                print("Commands:")
                for name, doc in commands:
                    display = name.ljust(20)
                    summary = f" - {doc}" if doc else ""
                    print(f"  {display}{summary}")
            except Exception:
                # if fallback fails, re-raise original
                raise
        else:
            raise
