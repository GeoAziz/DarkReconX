import json
import os

import pytest

# Skip the whole test module if FastAPI isn't present in the environment.
fastapi = pytest.importorskip("fastapi")
from starlette.testclient import TestClient

from api.app import app


def _default_headers():
    return {"X-API-Token": os.environ.get("DARKRECONX_API_TOKEN", "devtoken")}


def test_generate_and_retrieve_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # create results JSON that generator will consume
    os.makedirs("results", exist_ok=True)
    data = {"target": "example.com", "risk": {"score": 7}}
    with open("results/example.com.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh)

    client = TestClient(app)
    r = client.post("/generate_report", json={"target": "example.com", "format": "json"}, headers=_default_headers())
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"

    # Now retrieve via reports endpoint
    r2 = client.get("/reports/example.com", headers=_default_headers())
    assert r2.status_code == 200
    assert r2.json().get("risk", {}).get("score") == 7


def test_generate_report_missing_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.post("/generate_report", json={"target": "nope", "format": "json"}, headers=_default_headers())
    assert r.status_code == 404
