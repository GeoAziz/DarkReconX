import json
from pathlib import Path


def test_run_pipeline_single_target(monkeypatch, tmp_path):
    # Prepare a fake run_scan result
    fake_merged = {
        "success": True,
        "providers": ["dns", "whois"],
        "data": {"dns": {"A": ["example.com"]}},
        "errors": {},
        "scan_duration_seconds": 0.1,
    }

    async def fake_run_scan(target, profile="full", max_concurrent=5, timeout_per_provider=30.0):
        return fake_merged

    async def fake_batch_verify(urls, concurrency=10):
        return [{"url": "https://example.com", "status": 200, "live": True, "time_ms": 10}]

    # Patch the orchestrator and verifier
    import core.orchestrator as orchestrator
    import modules.utils.async_verify as av

    monkeypatch.setattr(orchestrator, "run_scan", fake_run_scan)
    monkeypatch.setattr(av, "batch_http_verify", fake_batch_verify)

    # Create a targets file
    targets_file = tmp_path / "targets.txt"
    targets_file.write_text("example.com\n")

    # Run pipeline CLI
    from engine.pipeline import run_pipeline_cli

    outdir = tmp_path / "out"
    res = run_pipeline_cli(str(targets_file), profile="full", verify_http=True, outdir=str(outdir))

    # Assertions: files created
    assert (outdir / "example.com.json").exists()
    assert (outdir / "summary.json").exists()
    assert (outdir / "summary.csv").exists()

    s = json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
    assert s["total_targets"] == 1
    assert "example.com" in s["targets"]


def test_html_report_generation(tmp_path):
    """Test that HTML report is generated correctly."""
    from engine.pipeline import _render_html_report

    summary = {
        "total_targets": 2,
        "targets": {
            "example.com": {
                "success": True,
                "providers": ["dns", "whois"],
                "live_hosts": ["www.example.com", "mail.example.com"],
                "errors": {},
                "scan_duration_seconds": 1.5,
            },
            "test.org": {
                "success": False,
                "providers": ["dns"],
                "live_hosts": [],
                "errors": {"dns": "timeout"},
                "scan_duration_seconds": 30.0,
            },
        },
    }

    html = _render_html_report(summary, str(tmp_path))

    # Check that the HTML contains expected content
    assert "DarkReconX Pipeline Report" in html
    assert "Total Targets" in html
    assert "example.com" in html
    assert "test.org" in html
    assert "Success" in html
    assert "Failed" in html
    assert "<table>" in html
    assert "2" in html  # total targets
    assert "1" in html  # successful scans
