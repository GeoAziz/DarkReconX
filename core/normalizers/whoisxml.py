"""
WhoisXML Normalizer

Converts WhoisXML API responses to UnifiedRecord format.

WhoisXML provides comprehensive WHOIS data with structured parsing.
Response structure:
{
    "WhoisRecord": {
        "domainName": "example.com",
        "registrarName": "Example Registrar, Inc.",
        "registryData": {
            "createdDate": "1995-08-14T04:00:00Z",
            "updatedDate": "2023-08-14T07:01:31Z",
            "expiresDate": "2024-08-13T04:00:00Z"
        },
        "registrant": {
            "organization": "Example Organization",
            "country": "US",
            "email": "admin@example.com"
        },
        "administrativeContact": {
            "email": "admin@example.com"
        },
        "technicalContact": {
            "email": "tech@example.com"
        },
        "nameServers": {
            "hostNames": ["ns1.example.com", "ns2.example.com"]
        }
    }
}

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from typing import Any, Dict

from core.unified_record import UnifiedRecord, create_empty_record


def normalize_whoisxml(resp: Dict[str, Any], target: str) -> UnifiedRecord:
    """
    Normalize WhoisXML response to UnifiedRecord format.

    Args:
        resp: Raw WhoisXML API response
        target: The domain being queried

    Returns:
        UnifiedRecord with WHOIS and DNS data populated

    Example:
        >>> resp = {"WhoisRecord": {"registrarName": "Example Registrar"}}
        >>> record = normalize_whoisxml(resp, "example.com")
        >>> record.whois["registrar"]
        'Example Registrar'
    """
    record = create_empty_record(source="whoisxml", target=target, target_type="domain")

    # Extract WhoisRecord
    whois_record = resp.get("WhoisRecord", {})

    # Extract registrar information
    record.whois["registrar"] = whois_record.get("registrarName")

    # Extract registrant data
    registrant = whois_record.get("registrant", {})
    if isinstance(registrant, dict):
        record.whois["org"] = registrant.get("organization")
        record.whois["country"] = registrant.get("country")

        # Extract registrant email
        registrant_email = registrant.get("email")
        if registrant_email and registrant_email not in record.whois["emails"]:
            record.whois["emails"].append(registrant_email)

    # Extract additional contact emails
    for contact_type in ["administrativeContact", "technicalContact", "billingContact"]:
        contact = whois_record.get(contact_type, {})
        if isinstance(contact, dict):
            contact_email = contact.get("email")
            if contact_email and contact_email not in record.whois["emails"]:
                record.whois["emails"].append(contact_email)

    # Extract registry dates
    registry_data = whois_record.get("registryData", {})
    if isinstance(registry_data, dict):
        record.whois["created"] = registry_data.get("createdDate")
        record.whois["updated"] = registry_data.get("updatedDate")
        record.whois["expires"] = registry_data.get("expiresDate")

    # Fallback to top-level dates if registry data not available
    if not record.whois["created"]:
        record.whois["created"] = whois_record.get("createdDate")
    if not record.whois["updated"]:
        record.whois["updated"] = whois_record.get("updatedDate")
    if not record.whois["expires"]:
        record.whois["expires"] = whois_record.get("expiresDate")

    # Extract name servers
    name_servers = whois_record.get("nameServers", {})
    if isinstance(name_servers, dict):
        host_names = name_servers.get("hostNames", [])
        if isinstance(host_names, list):
            record.resolved["ns"] = host_names

    # Alternative name server format
    if not record.resolved["ns"]:
        ns_list = whois_record.get("nameServersList")
        if isinstance(ns_list, list):
            record.resolved["ns"] = ns_list

    # Extract contact country if not in registrant
    if not record.whois["country"]:
        admin_contact = whois_record.get("administrativeContact", {})
        if isinstance(admin_contact, dict):
            record.whois["country"] = admin_contact.get("country")

    # Preserve raw response
    record.raw = resp

    return record


def normalize_whoisxml_ip(resp: Dict[str, Any], target: str) -> UnifiedRecord:
    """
    Normalize WhoisXML IP WHOIS response to UnifiedRecord format.

    WhoisXML also provides IP WHOIS data with different structure.

    Args:
        resp: Raw WhoisXML IP WHOIS API response
        target: The IP address being queried

    Returns:
        UnifiedRecord with network and WHOIS data populated
    """
    record = create_empty_record(source="whoisxml", target=target, target_type="ip")

    # Extract IP WHOIS data
    ip_whois = resp.get("IpWhoisRecord", {})

    # Extract organization/ISP
    record.network["isp"] = ip_whois.get("org")
    record.whois["org"] = ip_whois.get("orgName", ip_whois.get("org"))

    # Extract country
    record.network["country"] = ip_whois.get("country")
    record.whois["country"] = ip_whois.get("country")

    # Extract ASN
    asn = ip_whois.get("asn")
    if asn:
        # Ensure ASN has 'AS' prefix
        asn_str = str(asn)
        if not asn_str.startswith("AS"):
            asn_str = f"AS{asn_str}"
        record.network["asn"] = asn_str

    record.network["asn_name"] = ip_whois.get("asnName")

    # Extract city and region
    record.network["city"] = ip_whois.get("city")
    record.network["region"] = ip_whois.get("region")

    # Extract contact emails
    contacts = ip_whois.get("contacts", [])
    if isinstance(contacts, list):
        for contact in contacts:
            if isinstance(contact, dict):
                email = contact.get("email")
                if email and email not in record.whois["emails"]:
                    record.whois["emails"].append(email)

    # Extract dates
    record.whois["created"] = ip_whois.get("createdDate")
    record.whois["updated"] = ip_whois.get("updatedDate")

    # Preserve raw response
    record.raw = resp

    return record


def is_whoisxml_response(data: Dict[str, Any]) -> bool:
    """
    Check if data looks like a WhoisXML response.

    Args:
        data: Dictionary to check

    Returns:
        True if it appears to be a WhoisXML response
    """
    return isinstance(data, dict) and ("WhoisRecord" in data or "IpWhoisRecord" in data)
