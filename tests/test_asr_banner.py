import asyncio

import pytest

from modules.asr.banner_grab import grab_banner


class DummyReader:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self, n=-1):
        await asyncio.sleep(0)
        return self._data


class DummyWriter:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    async def wait_closed(self):
        await asyncio.sleep(0)


def test_grab_banner_tcp(monkeypatch):
    # Mock asyncio.open_connection to return dummy reader/writer
    async def fake_open(host, port):
        return DummyReader(b"SSH-2.0-OpenSSH_7.4\r\n"), DummyWriter()

    monkeypatch.setattr(asyncio, "open_connection", fake_open)

    res = asyncio.run(grab_banner("localhost", 22, timeout=1))
    assert isinstance(res, dict)
    assert "banner" in res
    assert res["banner"] != ""


def test_grab_banner_http(monkeypatch):
    # Mock httpx AsyncClient and its head method
    class DummyResp:
        def __init__(self):
            self.headers = {"server": "nginx/1.18.0"}

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            return DummyResp()

    monkeypatch.setattr("modules.asr.banner_grab.httpx.AsyncClient", DummyClient)

    res = asyncio.run(grab_banner("example.com", 80, timeout=1))
    assert res["service"] == "http"
    assert "nginx" in res["banner"]
