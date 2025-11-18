from core.http_client import HTTPClient


def test_httpclient_direct_get():
    c = HTTPClient(use_tor=False)
    text = c.get("http://httpbin.org/ip")
    assert text is not None
    assert "origin" in text
