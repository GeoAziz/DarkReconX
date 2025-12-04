def risk_rules(asr_record):
    reasons = []
    score = 0
    # Expired cert
    tls = asr_record.get("tls", {})
    if tls.get("days_left", 1) < 1:
        reasons.append("expired_cert")
        score += 2
    if tls.get("weak_cipher"):
        reasons.append("weak_cipher")
        score += 1
    # Admin path
    paths = asr_record.get("paths", [])
    for p in paths:
        if p.get("status") == 200 or p.get("status") == 403:
            reasons.append("admin_path_found")
            score += 1
    # Outdated banner
    banner = asr_record.get("banner", "")
    if banner and any(x in banner for x in ["1.0", "0.9", "0.8"]):
        reasons.append("outdated_banner")
        score += 1
    # HTTP login page
    web = asr_record.get("web", {})
    if web.get("status") == 200 and any(x in web.get("title", "").lower() for x in ["login", "admin"]):
        reasons.append("http_login_page")
        score += 1
    return {"score": score, "reasons": reasons}
