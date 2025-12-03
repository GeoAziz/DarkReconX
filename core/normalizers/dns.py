"""
DNS Resolver Normalizer

Converts DNS resolver responses to UnifiedRecord format.

DNS resolvers return various formats:
- dnspython: Answer objects with rrsets
- asyncio resolvers: Lists of tuples
- system resolvers: Raw strings or lists

This normalizer handles all common DNS response formats and converts them
to the unified schema.

Example dnspython response:
- A records: [rdata.address for rdata in answer]
- MX records: [(rdata.preference, str(rdata.exchange)) for rdata in answer]
- NS records: [str(rdata) for rdata in answer]
- TXT records: [str(rdata) for rdata in answer]

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from typing import Any, Dict, List, Union
from core.unified_record import UnifiedRecord, create_empty_record


def normalize_dns(
    resp: Union[Dict[str, Any], List[Any]], 
    target: str,
    record_type: str = "A"
) -> UnifiedRecord:
    """
    Normalize DNS resolver response to UnifiedRecord format.
    
    Args:
        resp: Raw DNS response (can be dict, list, or dnspython Answer object)
        target: The domain being queried
        record_type: Type of DNS query ("A", "MX", "NS", "TXT")
    
    Returns:
        UnifiedRecord with resolved DNS data populated
    
    Example:
        >>> resp = {"A": ["93.184.216.34"], "NS": ["ns1.example.com"]}
        >>> record = normalize_dns(resp, "example.com")
        >>> record.resolved["ip"]
        ['93.184.216.34']
    """
    record = create_empty_record(
        source="dns",
        target=target,
        target_type="domain"
    )
    
    # Handle different response formats
    if isinstance(resp, dict):
        record = _normalize_dns_dict(resp, record)
    elif isinstance(resp, list):
        record = _normalize_dns_list(resp, record, record_type)
    else:
        # Try to handle dnspython Answer objects
        try:
            record = _normalize_dnspython_answer(resp, record, record_type)
        except Exception:
            # If all else fails, store as raw
            record.raw = {"response": str(resp), "type": record_type}
    
    return record


def _normalize_dns_dict(resp: Dict[str, Any], record: UnifiedRecord) -> UnifiedRecord:
    """
    Normalize dictionary-formatted DNS response.
    
    Expected format:
    {
        "A": ["93.184.216.34", "93.184.216.35"],
        "MX": ["10 mail.example.com"],
        "NS": ["ns1.example.com", "ns2.example.com"],
        "TXT": ["v=spf1 include:_spf.example.com ~all"]
    }
    """
    # Extract A records (IP addresses)
    a_records = resp.get("A", [])
    if isinstance(a_records, list):
        record.resolved["ip"].extend([str(ip) for ip in a_records if ip])
    elif a_records:
        record.resolved["ip"].append(str(a_records))
    
    # Extract MX records
    mx_records = resp.get("MX", [])
    if isinstance(mx_records, list):
        for mx in mx_records:
            if isinstance(mx, tuple):
                # Format: (priority, exchange)
                record.resolved["mx"].append(f"{mx[0]} {mx[1]}")
            elif isinstance(mx, str):
                record.resolved["mx"].append(mx)
    elif mx_records:
        record.resolved["mx"].append(str(mx_records))
    
    # Extract NS records
    ns_records = resp.get("NS", [])
    if isinstance(ns_records, list):
        record.resolved["ns"].extend([str(ns) for ns in ns_records if ns])
    elif ns_records:
        record.resolved["ns"].append(str(ns_records))
    
    # Extract TXT records
    txt_records = resp.get("TXT", [])
    if isinstance(txt_records, list):
        record.resolved["txt"].extend([str(txt) for txt in txt_records if txt])
    elif txt_records:
        record.resolved["txt"].append(str(txt_records))
    
    # Extract AAAA (IPv6) records - add to IP list
    aaaa_records = resp.get("AAAA", [])
    if isinstance(aaaa_records, list):
        record.resolved["ip"].extend([str(ip) for ip in aaaa_records if ip])
    elif aaaa_records:
        record.resolved["ip"].append(str(aaaa_records))
    
    # Store raw response
    record.raw = resp
    
    return record


def _normalize_dns_list(
    resp: List[Any], 
    record: UnifiedRecord, 
    record_type: str
) -> UnifiedRecord:
    """
    Normalize list-formatted DNS response.
    
    Args:
        resp: List of DNS records
        record: UnifiedRecord to populate
        record_type: Type of DNS records in the list
    """
    record_type = record_type.upper()
    
    if record_type == "A" or record_type == "AAAA":
        record.resolved["ip"].extend([str(item) for item in resp if item])
    elif record_type == "MX":
        for item in resp:
            if isinstance(item, tuple):
                record.resolved["mx"].append(f"{item[0]} {item[1]}")
            else:
                record.resolved["mx"].append(str(item))
    elif record_type == "NS":
        record.resolved["ns"].extend([str(item) for item in resp if item])
    elif record_type == "TXT":
        record.resolved["txt"].extend([str(item) for item in resp if item])
    
    record.raw = {"records": resp, "type": record_type}
    
    return record


def _normalize_dnspython_answer(
    answer: Any, 
    record: UnifiedRecord, 
    record_type: str
) -> UnifiedRecord:
    """
    Normalize dnspython Answer object.
    
    Args:
        answer: dnspython Answer object
        record: UnifiedRecord to populate
        record_type: Type of DNS query
    """
    try:
        # dnspython Answer objects are iterable
        record_type = record_type.upper()
        
        if record_type == "A" or record_type == "AAAA":
            for rdata in answer:
                record.resolved["ip"].append(str(rdata.address))
        
        elif record_type == "MX":
            for rdata in answer:
                mx_record = f"{rdata.preference} {str(rdata.exchange)}"
                record.resolved["mx"].append(mx_record)
        
        elif record_type == "NS":
            for rdata in answer:
                record.resolved["ns"].append(str(rdata))
        
        elif record_type == "TXT":
            for rdata in answer:
                # TXT records can have multiple strings
                txt_value = b"".join(rdata.strings).decode("utf-8", errors="ignore")
                record.resolved["txt"].append(txt_value)
        
        record.raw = {"answer": str(answer), "type": record_type}
    
    except Exception as e:
        # If dnspython parsing fails, store as raw
        record.raw = {"error": str(e), "answer": str(answer), "type": record_type}
    
    return record


def normalize_dns_bulk(
    results: Dict[str, Dict[str, List[Any]]], 
    target: str
) -> UnifiedRecord:
    """
    Normalize bulk DNS results (all record types at once).
    
    Args:
        results: Dictionary with all DNS record types
        target: The domain being queried
    
    Returns:
        UnifiedRecord with all DNS data populated
    
    Example:
        >>> results = {
        ...     "A": ["93.184.216.34"],
        ...     "MX": ["10 mail.example.com"],
        ...     "NS": ["ns1.example.com"]
        ... }
        >>> record = normalize_dns_bulk(results, "example.com")
    """
    return normalize_dns(results, target)


def is_dns_response(data: Any) -> bool:
    """
    Check if data looks like a DNS response.
    
    Args:
        data: Data to check
    
    Returns:
        True if it appears to be a DNS response
    """
    if isinstance(data, dict):
        # Check for common DNS record type keys
        dns_keys = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"}
        return bool(dns_keys.intersection(data.keys()))
    
    # Could be a list of records or dnspython Answer
    return isinstance(data, list) or hasattr(data, "__iter__")
