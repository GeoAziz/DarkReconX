import asyncio
import json
import os
import socket

from engine.async_runner import AsyncEngine
from modules.asr.admin_path_scan import admin_path_scan
from modules.asr.banner_grab import grab_banner
from modules.asr.port_probe import port_probe
from modules.asr.remediation import remediation_suggestions
from modules.asr.risk_rules import risk_rules
from modules.asr.tls_inspect import tls_inspect
from modules.asr.web_fingerprint import web_fingerprint

ASR_SCHEMA = ["target", "ip", "port", "protocol", "service", "banner", "tls", "web", "paths", "risk", "raw"]


async def process_asr_target(target, ports, safe_mode=True, tls_check=True, banner=True, concurrency=100):
    # Resolve IP
    try:
        ip = socket.gethostbyname(target)
    except Exception:
        ip = target
    # Port scan
    probe = await port_probe(ip, ports, concurrency=concurrency)
    open_ports = probe["open_ports"]
    probe_time = probe["probe_time_ms"]
    results = []
    for port in open_ports:
        record = {
            "target": target,
            "ip": ip,
            "port": port,
            "protocol": "tcp",
            "service": None,
            "banner": None,
            "tls": {},
            "web": {},
            "paths": [],
            "risk": {},
            "raw": {},
        }
        # Banner
        if banner:
            b = await grab_banner(ip, port)
            record.update(b)
            record["banner"] = b.get("banner", "")
            record["service"] = b.get("service", "")
            record["raw"]["banner"] = b
        # TLS
        if tls_check and port == 443:
            t = await tls_inspect(ip, port)
            record["tls"] = t
            record["raw"]["tls"] = t
        # Web fingerprint
        if port in (80, 443):
            w = await web_fingerprint(ip, port)
            record["web"] = w
            record["raw"]["web"] = w
        # Admin paths
        if not safe_mode and port in (80, 443):
            p = await admin_path_scan(ip, port, safe_mode=safe_mode)
            record["paths"] = p.get("paths", [])
            record["raw"]["paths"] = p
        # Risk
        risk = risk_rules(record)
        record["risk"] = risk
        # Remediation
        record["remediation"] = remediation_suggestions(risk.get("reasons", []))
        results.append(record)
    return results


async def run_asr(targets, ports, safe_mode=True, tls_check=True, banner=True, concurrency=100, outdir="results/asr"):
    os.makedirs(outdir, exist_ok=True)
    engine = AsyncEngine(max_concurrency=concurrency)
    all_results = []
    tasks = [engine.run_task(process_asr_target(t, ports, safe_mode, tls_check, banner, concurrency)) for t in targets]
    for coro, target in zip(asyncio.as_completed(tasks), targets):
        res = await coro
        all_results.extend(res)
        # Save per target
        with open(f"{outdir}/{target}.json", "w") as f:
            json.dump(res, f, indent=2)
    # Save summary
    with open(f"{outdir}_summary.json", "w") as f:
        json.dump(all_results, f, indent=2)
    return all_results
