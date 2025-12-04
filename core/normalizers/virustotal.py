"""
VirusTotal Normalizer

Converts VirusTotal API responses to UnifiedRecord format.

VirusTotal provides threat intelligence, malware detection, and URL/domain reputation data.
Response structure varies by endpoint:

Domain report:
{
    "data": {
        "id": "example.com",
        "attributes": {
            "last_analysis_stats": {"malicious": 2, "suspicious": 0, "clean": 85},
            "last_dns_records": [...],
            "whois": "...",
            "reputation": -5,
            "categories": {"Forcepoint ThreatSeeker": "phishing"}
        }
    }
}

IP report:
{
    "data": {
        "id": "8.8.8.8",
        "attributes": {
            "asn": 15169,
            "as_owner": "Google LLC",
            "country": "US",
            "last_analysis_stats": {"malicious": 0, "suspicious": 0, "clean": 89},
            "reputation": 1459
        }
    }
}

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from typing import Any, Dict

from core.unified_record import UnifiedRecord, create_empty_record


def normalize_virustotal(resp: Dict[str, Any], target: str) -> UnifiedRecord:
    """
    Normalize VirusTotal response to UnifiedRecord format.

    Args:
        resp: Raw VirusTotal API response
        target: The domain/IP/URL being queried

    Returns:
        UnifiedRecord with risk, network, and DNS data populated

    Example:
        >>> resp = {"data": {"attributes": {"last_analysis_stats": {"malicious": 2}}}}
        >>> record = normalize_virustotal(resp, "example.com")
        >>> record.risk["malicious"]
        True
    """
    # Determine target type
    target_type = _determine_target_type(target)

    record = create_empty_record(source="virustotal", target=target, target_type=target_type)

    # Extract data from nested structure
    data = resp.get("data", {})
    attributes = data.get("attributes", {})

    # Extract threat intelligence / risk data
    analysis_stats = attributes.get("last_analysis_stats", {})
    malicious_count = analysis_stats.get("malicious", 0)
    suspicious_count = analysis_stats.get("suspicious", 0)
    clean_count = analysis_stats.get("clean", 0)

    # Calculate risk score (0-100)
    total_engines = malicious_count + suspicious_count + clean_count
    if total_engines > 0:
        risk_score = ((malicious_count + suspicious_count * 0.5) / total_engines) * 100
        record.risk["score"] = round(risk_score, 2)

    # Determine if malicious
    record.risk["malicious"] = malicious_count > 0

    # Extract categories
    categories = attributes.get("categories", {})
    if isinstance(categories, dict):
        record.risk["categories"] = list(set(categories.values()))
    elif isinstance(categories, list):
        record.risk["categories"] = categories

    # Extract network data (for IP queries)
    if "asn" in attributes:
        record.network["asn"] = f"AS{attributes['asn']}" if attributes["asn"] else None
        record.network["asn_name"] = attributes.get("as_owner")

    record.network["country"] = attributes.get("country")

    # Extract DNS records (for domain queries)
    dns_records = attributes.get("last_dns_records", [])
    if isinstance(dns_records, list):
        for dns_record in dns_records:
            if not isinstance(dns_record, dict):
                continue

            record_type = dns_record.get("type", "").upper()
            value = dns_record.get("value", "")

            if record_type == "A" and value:
                record.resolved["ip"].append(value)
            elif record_type == "MX" and value:
                record.resolved["mx"].append(value)
            elif record_type == "NS" and value:
                record.resolved["ns"].append(value)
            elif record_type == "TXT" and value:
                record.resolved["txt"].append(value)

    # Extract WHOIS data (if available)
    whois_data = attributes.get("whois")
    if whois_data:
        record.whois = _parse_virustotal_whois(whois_data)

    # Extract timestamps
    if "creation_date" in attributes:
        record.whois["created"] = str(attributes["creation_date"])
    if "last_modification_date" in attributes:
        record.whois["updated"] = str(attributes["last_modification_date"])

    # Preserve raw response
    record.raw = resp

    return record


def _determine_target_type(target: str) -> str:
    """
    Determine if target is a domain, IP, or URL.

    Args:
        target: The target string

    Returns:
        "domain", "ip", or "url"
    """
    if target.startswith(("http://", "https://")):
        return "url"

    # Simple IP detection (covers IPv4)
    if all(part.isdigit() and 0 <= int(part) <= 255 for part in target.split(".") if part) and target.count(".") == 3:
        return "ip"

    return "domain"


def _parse_virustotal_whois(whois_text: str) -> Dict[str, Any]:
    """
    Parse VirusTotal WHOIS text into structured data.

    Args:
        whois_text: Raw WHOIS text from VirusTotal

    Returns:
        Dictionary with parsed WHOIS fields
    """
    whois_dict = {
        "registrar": None,
        "org": None,
        "country": None,
        "emails": [],
        "created": None,
        "updated": None,
        "expires": None,
    }

    if not isinstance(whois_text, str):
        return whois_dict

    lines = whois_text.lower().split("\n")

    for line in lines:
        line = line.strip()

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not value:
            continue

        # Extract registrar
        if "registrar" in key and not whois_dict["registrar"]:
            whois_dict["registrar"] = value

        # Extract organization
        elif any(org_key in key for org_key in ["organization", "org"]) and not whois_dict["org"]:
            whois_dict["org"] = value

        # Extract country
        elif "country" in key and not whois_dict["country"]:
            whois_dict["country"] = value.upper()

        # Extract emails
        elif "email" in key or "@" in value:
            if "@" in value and value not in whois_dict["emails"]:
                whois_dict["emails"].append(value)

        # Extract dates
        elif "creation date" in key or "created" in key:
            whois_dict["created"] = value
        elif "updated date" in key or "modified" in key:
            whois_dict["updated"] = value
        elif "expir" in key:
            whois_dict["expires"] = value

    return whois_dict


def is_virustotal_response(data: Dict[str, Any]) -> bool:
    """
    Check if data looks like a VirusTotal response.

    Args:
        data: Dictionary to check

    Returns:
        True if it appears to be a VirusTotal response
    """
    return isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "attributes" in data["data"]
