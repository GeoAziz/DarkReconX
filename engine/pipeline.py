"""High-level pipeline orchestration for DarkReconX.

This module wires the provider orchestrator, async HTTP verification,
cache flags, and output generation into a simple end-to-end pipeline.
"""

import asyncio
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Template

from core import fusion as _fusion
from core.logger import get_logger
from core.orchestrator import run_scan
from core.profiles import add_module_usage, load_metadata, save_metadata, update_collection
from modules.utils.async_verify import batch_http_verify

logger = get_logger("pipeline")


def _extract_candidate_hosts(merged: Dict[str, Any]) -> List[str]:
    """Naively extract host-like strings from merged provider data.

    This looks for dotted strings (containing a dot) in nested values and
    returns a deduplicated list. It's intentionally permissive.
    """
    hosts = set()

    def _walk(obj: Any):
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
        elif isinstance(obj, str):
            s = obj.strip()
            if "." in s and " " not in s and not s.isdigit():
                # crude filter, skip long JSON blobs
                if len(s) < 256:
                    hosts.add(s)

    _walk(merged.get("data", {}))
    return sorted(hosts)


def _render_html_report(summary: Dict[str, Any], outdir: str = "results/pipeline") -> str:
    """Render an HTML report from the pipeline summary.

    Returns the HTML as a string.
    """
    total_targets = summary.get("total_targets", 0)
    total_success = sum(1 for v in summary.get("targets", {}).values() if v.get("success"))
    total_live_hosts = sum(len(v.get("live_hosts", [])) for v in summary.get("targets", {}).values())
    total_errors = sum(len(v.get("errors", {})) for v in summary.get("targets", {}).values())

    target_rows = []
    for target, data in summary.get("targets", {}).items():
        target_rows.append(
            {
                "target": target,
                "success": data.get("success", False),
                "live_hosts": len(data.get("live_hosts", [])),
                "providers": len(data.get("providers", [])),
                "errors": len(data.get("errors", {})),
                "duration": data.get("scan_duration_seconds", "-"),
            }
        )

    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DarkReconX Pipeline Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px; }
        h1 { color: #333; margin-bottom: 10px; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
        .stat-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-box.success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .stat-box.live { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-box.error { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .stat-number { font-size: 32px; font-weight: bold; }
        .stat-label { font-size: 14px; margin-top: 5px; opacity: 0.9; }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th { background: #f8f9fa; color: #333; padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid #dee2e6; }
        tr:hover { background: #f8f9fa; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .badge.success { background: #d4edda; color: #155724; }
        .badge.failed { background: #f8d7da; color: #721c24; }
        footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕵️ DarkReconX Pipeline Report</h1>
        <p style="color: #666; margin: 10px 0;">Generated at: <strong>{{ timestamp }}</strong></p>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{{ total_targets }}</div>
                <div class="stat-label">Total Targets</div>
            </div>
            <div class="stat-box success">
                <div class="stat-number">{{ total_success }}</div>
                <div class="stat-label">Successful Scans</div>
            </div>
            <div class="stat-box live">
                <div class="stat-number">{{ total_live_hosts }}</div>
                <div class="stat-label">Live Hosts Detected</div>
            </div>
            <div class="stat-box error">
                <div class="stat-number">{{ total_errors }}</div>
                <div class="stat-label">Errors Encountered</div>
            </div>
        </div>

        <h2 style="margin-top: 40px; color: #333;">📊 Target Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Target</th>
                    <th>Status</th>
                    <th>Live Hosts</th>
                    <th>Providers</th>
                    <th>Errors</th>
                    <th>Duration (s)</th>
                </tr>
            </thead>
            <tbody>
                {% for row in target_rows %}
                <tr>
                    <td><strong>{{ row.target }}</strong></td>
                    <td>
                        {% if row.success %}
                        <span class="badge success">✓ Success</span>
                        {% else %}
                        <span class="badge failed">✗ Failed</span>
                        {% endif %}
                    </td>
                    <td>{{ row.live_hosts }}</td>
                    <td>{{ row.providers }}</td>
                    <td>{{ row.errors }}</td>
                    <td>{{ row.duration }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <footer>
            <p>DarkReconX v1.0 | Pipeline Generated Automatically</p>
        </footer>
    </div>
</body>
</html>
"""

    template = Template(template_str)
    html = template.render(
        total_targets=total_targets,
        total_success=total_success,
        total_live_hosts=total_live_hosts,
        total_errors=total_errors,
        target_rows=target_rows,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    return html


async def run_pipeline_for_targets(
    targets: List[str],
    profile: str = "full",
    max_concurrent_providers: int = 5,
    timeout_per_provider: float = 30.0,
    verify_http: bool = True,
    verify_concurrency: int = 10,
    outdir: str = "results/pipeline",
    generate_html: bool = True,
) -> Dict[str, Any]:
    """Run the full async pipeline for a list of targets.

    Returns a summary dict with per-target results and overall stats.
    """
    outdir_path = Path(outdir)
    outdir_path.mkdir(parents=True, exist_ok=True)

    summary = {"targets": {}, "total_targets": len(targets)}

    for target in targets:
        logger.info(f"Running pipeline for target: {target}")
        try:
            merged = await run_scan(
                target, profile=profile, max_concurrent=max_concurrent_providers, timeout_per_provider=timeout_per_provider
            )
        except Exception as e:
            logger.error(f"Scan failed for {target}: {e}")
            summary["targets"][target] = {"success": False, "error": str(e)}
            continue

        # HTTP verification
        live_hosts = []
        verify_results = []
        if verify_http:
            candidates = _extract_candidate_hosts(merged)
            urls = []
            for h in candidates:
                # try both schemes; some providers may include scheme already
                if h.startswith("http://") or h.startswith("https://"):
                    urls.append(h)
                else:
                    urls.append(f"https://{h}")
                    urls.append(f"http://{h}")

            if urls:
                try:
                    verify_results = await batch_http_verify(urls, concurrency=verify_concurrency)
                    # consider live those with live==True
                    live_hosts = [r["url"] for r in verify_results if r.get("live")]
                except Exception as e:
                    logger.warning(f"HTTP verification failed for {target}: {e}")

        # Save per-target JSON
        out_json = outdir_path / f"{target}.json"
        try:
            with out_json.open("w", encoding="utf-8") as fh:
                json.dump({"merged": merged, "http_verify": verify_results}, fh, indent=2)
        except Exception as e:
            logger.error(f"Failed to write results for {target}: {e}")

        # Run fusion to compute confidence across collected provider data and persist
        try:
            sources = merged.get("data", {}) if isinstance(merged, dict) else {}
            fused = _fusion.fuse_domain(target, sources)
            meta = load_metadata(target) or {}
            meta["confidence"] = fused.get("confidence", 0.0)
            save_metadata(target, meta)
            add_module_usage(target, "pipeline")

            # Try to extract simple collections for profiles (domains, ips, emails)
            domains = []
            ips = []
            # DNS provider extraction heuristics
            dns = sources.get("dns")
            if isinstance(dns, dict):
                for key in ("A", "a", "addresses", "A_RECORDS"):
                    vals = dns.get(key)
                    if vals:
                        if isinstance(vals, list):
                            ips.extend([str(x) for x in vals])
                        else:
                            ips.append(str(vals))

            # whois emails
            whois = sources.get("whois")
            if isinstance(whois, dict):
                emails = whois.get("emails") or whois.get("email")
                if emails:
                    if isinstance(emails, list):
                        update_collection(target, "emails", emails)
                    else:
                        update_collection(target, "emails", [emails])

            # ipinfo or other provider that returns ip list
            info = sources.get("ipinfo")
            if isinstance(info, dict):
                ipaddr = info.get("ip")
                if ipaddr:
                    ips.append(str(ipaddr))

            # persist domains/ips if found
            if domains:
                update_collection(target, "domains", domains)
            if ips:
                update_collection(target, "ips", list(set(ips)))
        except Exception:
            # fusion should not break pipeline
            logger.debug("Fusion persistence failed for target %s", target)

        # Update summary
        summary["targets"][target] = {
            "success": merged.get("success", False),
            "providers": list(merged.get("providers", [])),
            "live_hosts": live_hosts,
            "errors": merged.get("errors", {}),
            "scan_duration_seconds": merged.get("scan_duration_seconds", None),
        }

    # Write summary CSV
    csv_path = outdir_path / "summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["target", "success", "live_hosts_count", "providers_count", "errors_count", "scan_duration_seconds"])
        for t, v in summary["targets"].items():
            writer.writerow(
                [
                    t,
                    v.get("success", False),
                    len(v.get("live_hosts", [])),
                    len(v.get("providers", [])),
                    len(v.get("errors", {})),
                    v.get("scan_duration_seconds", ""),
                ]
            )

    # Save JSON summary
    try:
        with (outdir_path / "summary.json").open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
    except Exception as e:
        logger.error(f"Failed to write pipeline summary: {e}")

    # Generate HTML report if requested
    if generate_html:
        try:
            html_content = _render_html_report(summary, outdir)
            html_path = outdir_path / "report.html"
            with html_path.open("w", encoding="utf-8") as fh:
                fh.write(html_content)
            logger.info(f"HTML report written to {html_path}")
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

    return summary


def run_pipeline_cli(targets_file: str, **kwargs) -> Dict[str, Any]:
    """Synchronous CLI-friendly wrapper around the async pipeline.

    `targets_file` may be a path containing one target per line, or a single target name.
    """
    if os.path.exists(targets_file):
        with open(targets_file, "r", encoding="utf-8") as fh:
            targets = [l.strip() for l in fh if l.strip()]
    else:
        targets = [targets_file]

    return asyncio.run(run_pipeline_for_targets(targets, **kwargs))
