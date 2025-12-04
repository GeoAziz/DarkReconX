import os

import pytest

# Skip the whole test module if FastAPI isn't present in the environment.
fastapi = pytest.importorskip("fastapi")
from starlette.testclient import TestClient

from api.app import app


def _default_headers():
    return {"X-API-Token": os.environ.get("DARKRECONX_API_TOKEN", "devtoken")}


def test_csv_and_markdown_download(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("results/reports", exist_ok=True)
    csv_content = "col1,col2\n1,2\n"
    md_content = "# Report\n\n- item1\n"
    with open("results/reports/example.com.csv", "w", encoding="utf-8") as fh:
        fh.write(csv_content)
    with open("results/reports/example.com.md", "w", encoding="utf-8") as fh:
        fh.write(md_content)

    client = TestClient(app)
    r = client.get("/reports/example.com?format=csv&download=true", headers=_default_headers())
    assert r.status_code == 200
    assert r.headers.get("Content-Disposition") is not None
    assert r.text == csv_content

    r2 = client.get("/reports/example.com?format=md&download=true", headers=_default_headers())
    assert r2.status_code == 200
    assert r2.headers.get("Content-Disposition") is not None
    assert r2.text == md_content
