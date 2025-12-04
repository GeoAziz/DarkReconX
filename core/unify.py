"""
Unification and Merge Engine for DarkReconX

This module implements the core merge engine that combines multiple UnifiedRecords
from different providers into a single, deduplicated, comprehensive record.

The merge engine:
- Combines data from multiple providers (IPInfo, VirusTotal, WhoisXML, DNS, etc.)
- Deduplicates arrays (NS, MX, TXT, IPs)
- Prioritizes newer timestamps
- Merges risk categories
- Selects first non-empty field if missing elsewhere
- Preserves all original provider raw payloads

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.unified_record import UnifiedRecord, create_empty_record, validate_record

logger = get_logger(__name__)


def merge_records(records: List[UnifiedRecord]) -> UnifiedRecord:
    """
    Merge multiple UnifiedRecords into a single comprehensive record.

    This is the main merge function that orchestrates the entire unification process.

    Args:
        records: List of UnifiedRecords from different providers

    Returns:
        Single merged UnifiedRecord with deduplicated and prioritized data

    Example:
        >>> record1 = UnifiedRecord(source="ipinfo", type="ip", target="8.8.8.8")
        >>> record2 = UnifiedRecord(source="virustotal", type="ip", target="8.8.8.8")
        >>> merged = merge_records([record1, record2])
        >>> merged.source
        'merged'
    """
    if not records:
        logger.warning("merge_records called with empty list")
        return create_empty_record("merged", "", "unknown")

    if len(records) == 1:
        logger.debug(f"Only one record to merge from source: {records[0].source}")
        return records[0]

    # Validate all records
    valid_records = [r for r in records if validate_record(r)]

    if not valid_records:
        logger.error("No valid records to merge")
        return create_empty_record("merged", "", "unknown")

    # Use first record as base
    base_record = valid_records[0]
    target = base_record.target
    target_type = base_record.type

    # Create merged record
    merged = create_empty_record(source="merged", target=target, target_type=target_type)

    # Merge each section
    merged.resolved = _merge_resolved(valid_records)
    merged.whois = _merge_whois(valid_records)
    merged.network = _merge_network(valid_records)
    merged.risk = _merge_risk(valid_records)

    # Preserve all raw responses
    merged.raw = _merge_raw_responses(valid_records)

    logger.info(f"Merged {len(valid_records)} records for target: {target}")

    return merged


def _merge_resolved(records: List[UnifiedRecord]) -> Dict[str, List[str]]:
    """
    Merge DNS resolution data from multiple records.

    Deduplicates IPs, MX, NS, and TXT records while preserving order.

    Args:
        records: List of UnifiedRecords

    Returns:
        Merged resolved dictionary with deduplicated lists
    """
    merged = {
        "ip": [],
        "mx": [],
        "ns": [],
        "txt": [],
    }

    # Use sets to track what we've seen (for deduplication)
    seen_ip = set()
    seen_mx = set()
    seen_ns = set()
    seen_txt = set()

    for record in records:
        # Merge IP addresses
        for ip in record.resolved.get("ip", []):
            if ip and ip not in seen_ip:
                merged["ip"].append(ip)
                seen_ip.add(ip)

        # Merge MX records
        for mx in record.resolved.get("mx", []):
            if mx and mx not in seen_mx:
                merged["mx"].append(mx)
                seen_mx.add(mx)

        # Merge NS records
        for ns in record.resolved.get("ns", []):
            if ns and ns not in seen_ns:
                merged["ns"].append(ns)
                seen_ns.add(ns)

        # Merge TXT records
        for txt in record.resolved.get("txt", []):
            if txt and txt not in seen_txt:
                merged["txt"].append(txt)
                seen_txt.add(txt)

    return merged


def _merge_whois(records: List[UnifiedRecord]) -> Dict[str, Any]:
    """
    Merge WHOIS data from multiple records.

    Prioritizes newer timestamps and non-empty values.

    Args:
        records: List of UnifiedRecords

    Returns:
        Merged WHOIS dictionary
    """
    merged = {
        "registrar": None,
        "org": None,
        "country": None,
        "emails": [],
        "created": None,
        "updated": None,
        "expires": None,
    }

    seen_emails = set()

    # Track timestamps for prioritization
    created_dates = []
    updated_dates = []
    expires_dates = []

    for record in records:
        whois = record.whois

        # Use first non-empty value for simple fields
        if not merged["registrar"] and whois.get("registrar"):
            merged["registrar"] = whois["registrar"]

        if not merged["org"] and whois.get("org"):
            merged["org"] = whois["org"]

        if not merged["country"] and whois.get("country"):
            merged["country"] = whois["country"]

        # Deduplicate emails
        for email in whois.get("emails", []):
            if email and email not in seen_emails:
                merged["emails"].append(email)
                seen_emails.add(email)

        # Collect timestamps for comparison
        if whois.get("created"):
            created_dates.append(whois["created"])
        if whois.get("updated"):
            updated_dates.append(whois["updated"])
        if whois.get("expires"):
            expires_dates.append(whois["expires"])

    # Select most appropriate timestamps
    merged["created"] = _select_earliest_date(created_dates)
    merged["updated"] = _select_latest_date(updated_dates)
    merged["expires"] = _select_latest_date(expires_dates)

    return merged


def _merge_network(records: List[UnifiedRecord]) -> Dict[str, Any]:
    """
    Merge network/geolocation data from multiple records.

    Prioritizes most specific/detailed information.

    Args:
        records: List of UnifiedRecords

    Returns:
        Merged network dictionary
    """
    merged: Dict[str, Any] = {
        "asn": None,
        "asn_name": None,
        "isp": None,
        "city": None,
        "region": None,
        "country": None,
    }

    for record in records:
        network = record.network

        # Use first non-empty value for each field
        if not merged["asn"] and network.get("asn"):
            merged["asn"] = network["asn"]

        if not merged["asn_name"] and network.get("asn_name"):
            merged["asn_name"] = network["asn_name"]

        if not merged["isp"] and network.get("isp"):
            merged["isp"] = network["isp"]

        if not merged["city"] and network.get("city"):
            merged["city"] = network["city"]

        if not merged["region"] and network.get("region"):
            merged["region"] = network["region"]

        if not merged["country"] and network.get("country"):
            merged["country"] = network["country"]

    return merged


def _merge_risk(records: List[UnifiedRecord]) -> Dict[str, Any]:
    """
    Merge threat intelligence and risk data from multiple records.

    Takes maximum risk score and combines all categories.
    Sets malicious=True if ANY provider reports it as malicious.

    Args:
        records: List of UnifiedRecords

    Returns:
        Merged risk dictionary
    """
    merged = {
        "score": None,
        "categories": [],
        "malicious": False,
    }

    scores = []
    seen_categories = set()

    for record in records:
        risk = record.risk

        # Collect risk scores
        if risk.get("score") is not None:
            scores.append(float(risk["score"]))

        # Merge categories (deduplicate)
        for category in risk.get("categories", []):
            if category and category not in seen_categories:
                merged["categories"].append(category)
                seen_categories.add(category)

        # Set malicious if ANY provider reports it
        if risk.get("malicious"):
            merged["malicious"] = True

    # Use maximum risk score (most conservative approach)
    if scores:
        merged["score"] = max(scores)

    return merged


def _merge_raw_responses(records: List[UnifiedRecord]) -> Dict[str, Any]:
    """
    Merge raw provider responses.

    Preserves all original responses keyed by provider name.

    Args:
        records: List of UnifiedRecords

    Returns:
        Dictionary with raw responses from all providers
    """
    merged_raw = {}

    for record in records:
        source = record.source
        if record.raw:
            merged_raw[source] = record.raw

    return merged_raw


def _select_earliest_date(dates: List[str]) -> Optional[str]:
    """
    Select the earliest date from a list of date strings.

    Args:
        dates: List of date strings (ISO format or similar)

    Returns:
        Earliest date string, or None if list is empty
    """
    if not dates:
        return None

    # Try to parse dates for comparison
    parsed_dates = []
    for date_str in dates:
        try:
            # Try common formats
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    parsed = datetime.strptime(date_str[:19], fmt[: len(date_str[:19])])
                    parsed_dates.append((parsed, date_str))
                    break
                except ValueError:
                    continue
        except Exception:
            # If parsing fails, keep the string
            pass

    if parsed_dates:
        # Return original string of earliest parsed date
        return min(parsed_dates, key=lambda x: x[0])[1]

    # If no dates could be parsed, return first one
    return dates[0]


def _select_latest_date(dates: List[str]) -> Optional[str]:
    """
    Select the latest date from a list of date strings.

    Args:
        dates: List of date strings (ISO format or similar)

    Returns:
        Latest date string, or None if list is empty
    """
    if not dates:
        return None

    # Try to parse dates for comparison
    parsed_dates = []
    for date_str in dates:
        try:
            # Try common formats
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    parsed = datetime.strptime(date_str[:19], fmt[: len(date_str[:19])])
                    parsed_dates.append((parsed, date_str))
                    break
                except ValueError:
                    continue
        except Exception:
            # If parsing fails, keep the string
            pass

    if parsed_dates:
        # Return original string of latest parsed date
        return max(parsed_dates, key=lambda x: x[0])[1]

    # If no dates could be parsed, return first one
    return dates[0]


def unify_provider_data(target: str, target_type: str, providers_data: Dict[str, Any]) -> UnifiedRecord:
    """
    High-level function to unify data from multiple providers.

    This function takes raw provider responses, normalizes them,
    and merges them into a single UnifiedRecord.

    Args:
        target: The target being enriched
        target_type: Type of target ("domain", "ip", "url")
        providers_data: Dictionary mapping provider names to their raw responses

    Returns:
        Merged UnifiedRecord

    Example:
        >>> data = {
        ...     "ipinfo": {"ip": "8.8.8.8", "city": "Mountain View"},
        ...     "virustotal": {"data": {"attributes": {"reputation": 1459}}}
        ... }
        >>> unified = unify_provider_data("8.8.8.8", "ip", data)
    """
    from core.normalizers import normalize_dns, normalize_ipinfo, normalize_virustotal, normalize_whoisxml

    records = []

    # Normalize each provider's data
    for provider, raw_data in providers_data.items():
        try:
            if provider == "ipinfo":
                record = normalize_ipinfo(raw_data, target)
                records.append(record)

            elif provider == "virustotal":
                record = normalize_virustotal(raw_data, target)
                records.append(record)

            elif provider == "whoisxml":
                record = normalize_whoisxml(raw_data, target)
                records.append(record)

            elif provider == "dns":
                record = normalize_dns(raw_data, target)
                records.append(record)

            else:
                logger.warning(f"Unknown provider: {provider}")

        except Exception as e:
            logger.error(f"Failed to normalize {provider} data: {e}")
            continue

    # Merge all records
    return merge_records(records)
