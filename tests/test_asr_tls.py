import asyncio
from datetime import datetime, timedelta

import pytest

import modules.asr.tls_inspect as tls_inspect


class DummyCert:
    def __init__(self):
        class Issuer:
            def rfc4514_string(self):
                return "CN=Test CA,O=Example"

        self.issuer = Issuer()
        self.not_valid_before = datetime.utcnow() - timedelta(days=10)
        self.not_valid_after = datetime.utcnow() + timedelta(days=30)

        class Extensions:
            def get_extension_for_class(self, cls):
                class ExtVal:
                    def get_values_for_type(self, t):
                        return ["www.example.com", "api.example.com"]

                class Ext:
                    value = ExtVal()

                return Ext()

        self.extensions = Extensions()

        class SigAlg:
            name = "sha256"

        self.signature_hash_algorithm = SigAlg()


def test_tls_inspect_monkeypatched(monkeypatch):
    async def fake_fetch(host, port=443, timeout=5):
        return DummyCert()

    monkeypatch.setattr(tls_inspect, "fetch_cert", fake_fetch)
    res = asyncio.run(tls_inspect.tls_inspect("example.com", 443, timeout=1))
    assert res["issuer"] == "CN=Test CA,O=Example"
    assert "www.example.com" in res["san"]
    assert res["days_left"] > 0
    assert res["weak_cipher"] == False
