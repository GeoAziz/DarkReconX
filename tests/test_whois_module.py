from modules.whois_lookup.scanner import WhoisModule


class FakeWhois:
    def __init__(self):
        self.registrar = "ExampleRegistrar"
        self.creation_date = "2000-01-01"
        self.expiration_date = "2030-01-01"
        self.name_servers = ["ns1.example.com", "ns2.example.com"]


def test_whois_module(monkeypatch, tmp_path):
    def fake_whois(domain):
        return FakeWhois()

    monkeypatch.setattr("modules.whois_lookup.scanner._pywhois.whois", fake_whois)

    mod = WhoisModule()
    out = mod.run("example.com", use_tor=False, output=str(tmp_path / "whois.json"))
    assert out is not None
    assert out["domain"] == "example.com"
    # file written
    assert (tmp_path / "whois.json").exists()
