from core import correlation
from typing import cast, Dict, List


def test_correlate_domains_by_ip():
    profile = {
        "domains": [
            {"domain": "a.com", "ip": "1.1.1.1"},
            {"domain": "b.com", "ip": "1.1.1.1"},
            {"domain": "c.com", "ip": "2.2.2.2"},
        ]
    }

    res = correlation.correlate_domains_by_ip(profile)
    # Expect one correlated IP with two domains
    assert any(r[0] == "1.1.1.1" and set(r[1]) >= {"a.com", "b.com"} for r in res)

def test_detect_shared_asn():
    profile = cast(Dict[str, List[str]], {
        "domains": [
            {"domain": "a.com", "asn": "AS1"},
            {"domain": "b.com", "asn": "AS1"},
            {"domain": "c.com", "asn": "AS2"},
        ]
    })
    res = correlation.detect_shared_asn(profile)
    assert any(r[0] == "AS1" and set(r[1]) >= {"a.com", "b.com"} for r in res)
    assert any(r[0] == "AS1" and set(r[1]) >= {"a.com", "b.com"} for r in res)
