"""
IPInfo.io Normalizer

Converts IPInfo.io API responses to UnifiedRecord format.

IPInfo.io provides geolocation and network data for IP addresses.
Response structure:
{
    "ip": "8.8.8.8",
    "hostname": "dns.google",
    "city": "Mountain View",
    "region": "California",
    "country": "US",
    "loc": "37.4056,-122.0775",
    "org": "AS15169 Google LLC",
    "postal": "94043",
    "timezone": "America/Los_Angeles",
    "asn": {
        "asn": "AS15169",
        "name": "Google LLC",
        "domain": "google.com",
        "route": "8.8.8.0/24",
        "type": "hosting"
    }
}

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from typing import Any, Dict

from core.unified_record import UnifiedRecord, create_empty_record


def normalize_ipinfo(resp: Dict[str, Any], target: str) -> UnifiedRecord:
    """
    Normalize IPInfo.io response to UnifiedRecord format.

    Args:
        resp: Raw IPInfo.io API response
        target: The IP address being queried

    Returns:
        UnifiedRecord with network and geolocation data populated

    Example:
        >>> resp = {"ip": "8.8.8.8", "city": "Mountain View", "asn": {"asn": "AS15169"}}
        >>> record = normalize_ipinfo(resp, "8.8.8.8")
        >>> record.network["city"]
        'Mountain View'
    """
    record = create_empty_record(source="ipinfo", target=target, target_type="ip")

    # Extract ASN information
    asn_data = resp.get("asn", {})
    if isinstance(asn_data, dict):
        record.network["asn"] = asn_data.get("asn")
        record.network["asn_name"] = asn_data.get("name")

    # Extract organization/ISP
    record.network["isp"] = resp.get("org")

    # Extract geolocation data
    record.network["city"] = resp.get("city")
    record.network["region"] = resp.get("region")
    record.network["country"] = resp.get("country")

    # Add hostname to resolved IPs if available
    hostname = resp.get("hostname")
    if hostname:
        record.resolved["ip"] = [hostname]

    # Preserve raw response
    record.raw = resp

    return record


def is_ipinfo_response(data: Dict[str, Any]) -> bool:
    """
    Check if data looks like an IPInfo.io response.

    Args:
        data: Dictionary to check

    Returns:
        True if it appears to be an IPInfo response
    """
    # IPInfo responses typically have 'ip' and either 'city' or 'org'
    return isinstance(data, dict) and "ip" in data and ("city" in data or "org" in data or "country" in data)
