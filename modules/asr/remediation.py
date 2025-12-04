def remediation_suggestions(risk_reasons):
    suggestions = []
    for reason in risk_reasons:
        if reason == "expired_cert":
            suggestions.append("Renew TLS certificate; enable automatic renewal.")
        elif reason == "admin_path_found":
            suggestions.append("Restrict admin paths by IP; require authentication; move to VPN.")
        elif reason == "outdated_banner":
            suggestions.append("Upgrade service or obfuscate version in server banner.")
        elif reason == "http_login_page":
            suggestions.append("Enforce HTTPS for login pages; use strong authentication.")
        elif reason == "weak_cipher":
            suggestions.append("Disable weak ciphers; use strong TLS configuration.")
    return suggestions
