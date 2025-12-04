import modules.email_osint.scanner as emod


class DummyTXT:
    def __init__(self, s):
        # mimic dnspython's rdata with strings attribute
        self.strings = [s.encode()]

    def __str__(self):
        return self.strings[0].decode()


class DummyMX:
    def __init__(self, exchange):
        self.exchange = exchange


def test_email_osint(monkeypatch):
    # Mock dns.resolver.resolve
    def fake_resolve(name, qtype):
        if qtype == "MX":
            return [DummyMX("mx1.example.com."), DummyMX("mx2.example.com.")]
        if qtype == "TXT":
            if name.startswith("_dmarc"):
                return [DummyTXT("v=DMARC1; p=none;")]
            if name.endswith("example.com"):
                return [DummyTXT("v=spf1 include:_spf.example.com ~all")]
        raise Exception("No records")

    # Patch the resolver used by the module directly to avoid interference
    monkeypatch.setattr(emod.dns.resolver, "resolve", fake_resolve)

    res = emod.EmailOsintModule().run("alice@example.com")
    assert res["status"] == "ok"
    data = res["data"]
    assert data["valid_format"] is True
    assert data["domain"] == "example.com"
    assert "mx1.example.com" in data["mx_records"]
    assert data["spf"].startswith("v=spf1")
    assert data["dmarc"].lower().startswith("v=dmarc1")
