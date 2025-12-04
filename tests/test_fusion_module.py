from core import fusion


def test_compute_confidence_basic():
    sources = {"a": {}, "b": {"x": 1}}
    c = fusion.compute_confidence(sources)
    # successful=1, total=2 => 0.5
    assert isinstance(c, float)
    assert c == 0.5


def test_fuse_domain_shape():
    sources = {"virustotal": {"score": 10}, "ipinfo": {"asn": "AS1"}}
    out = fusion.fuse_domain("target.com", sources)
    assert out.get("domain") == "target.com"
    assert "sources" in out and "confidence" in out
    assert 0.0 <= out["confidence"] <= 1.0
