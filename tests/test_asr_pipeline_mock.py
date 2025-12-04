import asyncio

import pytest

from engine.asr_pipeline import process_asr_target
from modules.asr import admin_path_scan as ap
from modules.asr import banner_grab as bg
from modules.asr import port_probe as pp
from modules.asr import remediation as rem
from modules.asr import risk_rules as rr
from modules.asr import tls_inspect as ti
from modules.asr import web_fingerprint as wf


class DummyPortProbe:
    async def port_probe(self, host, ports, concurrency=100, timeout=3):
        return {"open_ports": [80], "probe_time_ms": 10}


def test_process_asr_target_monkeypatched(monkeypatch):
    # Monkeypatch functions in engine.asr_pipeline namespace (they were imported there)
    async def fake_port_probe(host, ports, concurrency=100, timeout=3):
        return {"open_ports": [80], "probe_time_ms": 10}

    monkeypatch.setattr("engine.asr_pipeline.port_probe", fake_port_probe)

    async def fake_grab_banner(host, port, timeout=5):
        return {"banner": "nginx/1.18.0", "service": "http", "product": "nginx", "version": "1.18.0"}

    monkeypatch.setattr("engine.asr_pipeline.grab_banner", fake_grab_banner)

    async def fake_tls(host, port, timeout=5):
        return {
            "issuer": "CN=Test",
            "san": ["example.com"],
            "valid_from": "2020-01-01",
            "valid_to": "2030-01-01",
            "days_left": 100,
            "weak_cipher": False,
        }

    monkeypatch.setattr("engine.asr_pipeline.tls_inspect", fake_tls)

    async def fake_wf(host, port, timeout=5):
        return {"status": 200, "title": "Test", "tech": ["nginx"], "server_header": "nginx/1.18"}

    monkeypatch.setattr("engine.asr_pipeline.web_fingerprint", fake_wf)

    async def fake_ap(host, port, timeout=5, safe_mode=True):
        return {"paths": [{"path": "/admin", "status": 403}]}

    monkeypatch.setattr("engine.asr_pipeline.admin_path_scan", fake_ap)

    monkeypatch.setattr("engine.asr_pipeline.risk_rules", lambda rec: {"score": 2, "reasons": ["admin_path_found"]})
    monkeypatch.setattr("engine.asr_pipeline.remediation_suggestions", lambda reasons: ["Restrict admin paths by IP"])

    res = asyncio.run(process_asr_target("localhost", [80], safe_mode=True, tls_check=True, banner=True, concurrency=10))
    assert isinstance(res, list)
    assert len(res) == 1
    rec = res[0]
    assert rec["target"] == "localhost"
    assert rec["port"] == 80
    assert "tls" in rec
    assert "web" in rec
    assert "risk" in rec
