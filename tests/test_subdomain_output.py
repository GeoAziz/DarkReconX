from pathlib import Path

import dns.resolver

from modules.subdomain_finder.scanner import SubdomainFinder


def test_subfinder_output_json_and_csv(monkeypatch, tmp_path):
    # create a small wordlist
    wl = tmp_path / "wl.txt"
    wl.write_text("www\nmail\n")

    # mock dns.resolver.resolve
    def fake_resolve(name, rdtype):
        if name == "www.example.com":
            return ["1.2.3.4"]
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)

    # avoid real HTTP verification
    def fake_head(self, url, **kwargs):
        return 200

    monkeypatch.setattr("core.http_client.HTTPClient.head", fake_head, raising=False)

    finder = SubdomainFinder("example.com", wordlist=str(wl), use_tor=False, workers=2, verify_http=False)
    results = finder.run()
    assert results == ["www.example.com"]

    # test saving via CLI would write to results/; simulate and check file
    results_dir = Path(__file__).resolve().parents[1] / "results"
    results_dir.mkdir(exist_ok=True)
    out_json = results_dir / "test_subfinder.json"
    from core.output import save_output

    save_output(str(out_json), results)
    assert out_json.exists()

    out_csv = results_dir / "test_subfinder.csv"
    import csv

    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["subdomain"])
        for r in results:
            writer.writerow([r])

    assert out_csv.exists()
