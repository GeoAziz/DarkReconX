import types

import modules.github_osint.scanner as ghmod


class DummyResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")


def test_github_osint_exists(monkeypatch):
    # Mock httpx.get
    def fake_get(url, **kwargs):
        if url.endswith("/nonexistent"):
            return DummyResp(404, {})
        return DummyResp(200, {"login": "alice", "name": "Alice", "followers": 5, "public_repos": 2, "created_at": "2020-01-01"})

    monkeypatch.setattr("httpx.get", fake_get)

    # exists false
    res = ghmod.GithubOsintModule().run("nonexistent")
    assert res["status"] == "ok"
    assert res["data"]["exists"] is False

    # exists true
    res2 = ghmod.GithubOsintModule().run("alice")
    assert res2["status"] == "ok"
    assert res2["data"]["exists"] is True
    assert res2["data"]["profile"]["login"] == "alice"
