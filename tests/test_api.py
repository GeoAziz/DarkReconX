import os

import pytest

# Skip the whole test module if FastAPI isn't present in the environment.
fastapi = pytest.importorskip("fastapi")
from starlette.testclient import TestClient

from api.app import app


def _default_headers():
    return {"X-API-Token": os.environ.get("DARKRECONX_API_TOKEN", "devtoken")}


def test_scan_endpoint_queues_job(tmp_path, monkeypatch):
    # Ensure results/jobs exists in tmp and monkeypatch cwd to tmp
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.post("/scan", json={"target": "example.com"}, headers=_default_headers())
    assert r.status_code in (200, 202)
    data = r.json()
    assert "job_id" in data


def test_get_results_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.get("/results/nonexistent-target", headers=_default_headers())
    assert r.status_code == 404
