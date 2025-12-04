import json
import os

import pytest

# Skip the whole test module if FastAPI isn't present in the environment.
fastapi = pytest.importorskip("fastapi")
from starlette.testclient import TestClient

from api.app import app


def _default_headers():
    return {"X-API-Token": os.environ.get("DARKRECONX_API_TOKEN", "devtoken")}


def test_report_json_served(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # create results/reports and a json report
    os.makedirs("results/reports", exist_ok=True)
    data = {"target": "example.com", "risk": {"score": 5}}
    with open("results/reports/example.com.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh)

    client = TestClient(app)
    r = client.get("/reports/example.com", headers=_default_headers())
    assert r.status_code == 200
    assert r.json().get("risk", {}).get("score") == 5


def test_report_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.get("/reports/missing-target", headers=_default_headers())
    assert r.status_code == 404
