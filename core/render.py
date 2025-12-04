"""Global rendering utilities for DarkReconX.

Provides consistent CLI output: headers, tables, pretty JSON, markdown export,
and a summary builder used across the application.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled header section."""
    content = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        content += f"\n[white]{subtitle}[/white]"
    console.print(Panel(content, title="[bold yellow]DarkReconX[/bold yellow]", box=box.ROUNDED))


def pretty_json(data: Any) -> None:
    """Print pretty JSON to the console."""
    try:
        # Use pretty-printed JSON for consistent testable output
        console.print(json.dumps(data, indent=2, default=str))
    except Exception:
        console.print(str(data))


def table_from_mapping(title: str, mapping: Dict[str, Any], limit: int = 10) -> None:
    """Render a simple two-column table from a mapping."""
    t = Table(title=title, box=box.SIMPLE)
    t.add_column("Field", style="cyan", no_wrap=True)
    t.add_column("Value", style="white")
    count = 0
    for k, v in mapping.items():
        if count >= limit:
            break
        val = v
        if isinstance(v, (list, dict)):
            val = json.dumps(v, default=str)
        t.add_row(str(k), str(val))
        count += 1
    console.print(t)


def build_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a unified high-level summary from provider data.

    This function is intentionally conservative: it extracts common keys
    like IPs, whois registration status, DNS counts, ASN and location.
    """
    summary: Dict[str, Any] = {}
    # target
    summary["target"] = data.get("target") or data.get("domain")

    # IPs
    resolved = data.get("resolved", {}) if isinstance(data.get("resolved"), dict) else {}
    ips = resolved.get("ip") or []
    summary["ips_found"] = len(ips) if isinstance(ips, list) else (1 if ips else 0)

    # Whois
    whois = data.get("whois", {}) if isinstance(data.get("whois"), dict) else {}
    summary["whois_registered"] = bool(whois.get("registrar") or whois.get("org") or whois.get("created"))

    # DNS counts
    dns_counts = {}
    for r in ("ip", "mx", "ns", "txt", "a", "aaaa"):
        vals = resolved.get(r) if isinstance(resolved.get(r), list) else resolved.get(r) or []
        dns_counts[r] = len(vals) if isinstance(vals, list) else (1 if vals else 0)
    summary["dns_counts"] = dns_counts

    # ASN / location
    network = data.get("network") or {}
    summary["asn"] = network.get("asn")
    summary["location"] = ", ".join(filter(None, [network.get("city"), network.get("country")]))

    return summary


def render_output(data: Dict[str, Any], format_type: str = "pretty", verbosity: int = 0) -> None:
    """Unified render entrypoint used by the CLI.

    Args:
        data: UnifiedRecord-like dict
        format_type: 'pretty'|'json'|'md'
        verbosity: 0 (normal), 1 (verbose), 2 (debug/raw)
    """
    if format_type == "json":
        pretty_json(data)
        return

    if format_type == "md":
        # Simple markdown export
        lines: List[str] = []
        lines.append(f"# Report: {data.get('target', 'unknown')}")
        summary = build_summary(data)
        lines.append("\n## Summary")
        for k, v in summary.items():
            lines.append(f"- **{k}**: {v}")
        # Add raw sections if verbose
        if verbosity >= 1:
            lines.append("\n## Raw Data")
            lines.append("```json")
            lines.append(json.dumps(data, indent=2, default=str))
            lines.append("```")
        console.print("\n".join(lines))
        return

    # default: pretty
    header(str(data.get("target", "Unknown")), subtitle=data.get("type"))
    summary = build_summary(data)
    table_from_mapping("Summary", summary)

    # Show whois and network when verbosity is enabled
    if verbosity >= 1:
        whois = data.get("whois") or {}
        if whois:
            table_from_mapping("WHOIS", whois, limit=20)
        network = data.get("network") or {}
        if network:
            table_from_mapping("Network", network, limit=20)
