from core.http_client import HTTPClient
import pytest


def test_httpclient_direct_get():
    c = HTTPClient(use_tor=False)
    text = c.get("http://httpbin.org/ip")
    if text is None:
        pytest.skip("httpbin.org appears unreachable or returned an error; skipping integration test")
    assert "origin" in text
