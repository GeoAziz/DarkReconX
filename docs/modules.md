# Modules added in Day 21

This document lists the Day 21 modules and their brief descriptions.

## github_osint

- Purpose: Passive GitHub reconnaissance for public profile metadata.
- What it returns: existence flag, profile metadata (name, followers, public_repos, created_at), optional repo list (name, stars, language).
- Safety: Uses only public GitHub REST API endpoints. No cloning, no private data access.

## email_osint

- Purpose: Email address validation and passive domain checks (MX, SPF, DMARC, DKIM existence checks).
- What it returns: valid_format, domain, mx_records, spf, dmarc, dkim.
- Safety: Passive DNS/TXT lookups only.

## ssl_info

- Purpose: Retrieve public SSL/TLS certificate metadata from a host (issuer, validity dates, SANs, days left).
- What it returns: common_name, issuer, valid_from, valid_to, days_left, san.
- Safety: Passive TLS handshake to fetch public certificate; no certificate transparency scraping or downloads beyond the public cert.

All modules return the standardized envelope: `{'module': '<name>', 'status': 'ok'|'error', 'data': {...}}`.
