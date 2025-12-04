from modules.asr.risk_rules import risk_rules


def test_risk_rules_expired_and_admin():
    rec = {"tls": {"days_left": -1, "weak_cipher": False}, "paths": [{"path": "/admin", "status": 200}], "banner": "nginx/1.0"}
    r = risk_rules(rec)
    assert "expired_cert" in r["reasons"]
    assert "admin_path_found" in r["reasons"]
    assert r["score"] >= 2


def test_risk_rules_outdated_banner_and_login():
    rec = {
        "tls": {"days_left": 100, "weak_cipher": False},
        "paths": [],
        "banner": "service/0.8",
        "web": {"status": 200, "title": "Admin Login"},
    }
    r = risk_rules(rec)
    assert "outdated_banner" in r["reasons"]
    assert "http_login_page" in r["reasons"]
