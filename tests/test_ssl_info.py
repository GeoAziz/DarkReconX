import modules.ssl_info.scanner as smod


class FakeSSLSock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getpeercert(self):
        return {
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("organizationName", "Let\'s Encrypt"),),),
            "notBefore": "Nov 15 12:00:00 2025 GMT",
            "notAfter": "Feb 15 12:00:00 2026 GMT",
            "subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com")),
        }


class FakeSockConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ssl_info(monkeypatch):
    # Monkeypatch socket.create_connection and SSLContext.wrap_socket
    monkeypatch.setattr("socket.create_connection", lambda addr, timeout=5: FakeSockConn())

    class FakeCtx:
        def wrap_socket(self, sock, server_hostname=None):
            return FakeSSLSock()

    monkeypatch.setattr("ssl.create_default_context", lambda: FakeCtx())

    res = smod.SSLInfoModule().run("example.com")
    assert res["status"] == "ok"
    d = res["data"]
    assert d["common_name"] == "example.com"
    assert "www.example.com" in d["san"]
