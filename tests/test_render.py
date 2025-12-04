import json

from core import render


def test_build_summary_basic():
    data = {
        "target": "example.com",
        "resolved": {"ip": ["1.2.3.4", "5.6.7.8"], "mx": ["mx1.example.com"]},
        "whois": {"registrar": "ExampleReg", "org": "Example Org"},
        "network": {"asn": "AS12345", "city": "Berlin", "country": "DE"},
    }
    s = render.build_summary(data)
    assert s["target"] == "example.com"
    assert s["ips_found"] == 2
    assert s["whois_registered"] is True
    assert isinstance(s["dns_counts"], dict)
    assert s["asn"] == "AS12345"
    assert "Berlin" in s["location"]


def test_render_output_json(capsys):
    data = {"target": "example.com", "foo": "bar"}
    render.render_output(data, format_type="json")
    captured = capsys.readouterr()
    # JSON output should include the key
    assert '"foo": "bar"' in captured.out


def test_render_output_md(capsys):
    data = {"target": "example.com", "resolved": {"ip": ["1.2.3.4"]}}
    render.render_output(data, format_type="md", verbosity=1)
    captured = capsys.readouterr()
    assert "# Report: example.com" in captured.out
    assert "## Summary" in captured.out
    # Raw JSON block should be present at verbosity=1
    assert "```json" in captured.out
