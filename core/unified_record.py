"""
Unified Record Schema for DarkReconX

This module defines the canonical data structure that ALL providers must output.
Every enrichment provider (IPInfo, WhoisXML, VirusTotal, DNS, etc.) returns
different data structures. This unified schema ensures consistency across the framework.

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


class ResolvedData(TypedDict, total=False):
    """DNS resolution data"""

    ip: List[str]
    mx: List[str]
    ns: List[str]
    txt: List[str]


class WhoisData(TypedDict, total=False):
    """WHOIS registration data"""

    registrar: Optional[str]
    org: Optional[str]
    country: Optional[str]
    emails: List[str]
    created: Optional[str]
    updated: Optional[str]
    expires: Optional[str]


class NetworkData(TypedDict, total=False):
    """Network/geolocation data"""

    asn: Optional[str]
    asn_name: Optional[str]
    isp: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]


class RiskData(TypedDict, total=False):
    """Threat intelligence data"""

    score: Optional[float]
    categories: List[str]
    malicious: bool


@dataclass
class UnifiedRecord:
    """
    The canonical data structure for all provider outputs.

    This structure must be the ONLY output format for all providers.
    Any provider-specific data should be preserved in the 'raw' field.

    Attributes:
        source: Provider name (e.g., "ipinfo", "virustotal", "whoisxml")
        type: Target type - "domain", "ip", or "url"
        target: The target being enriched (domain name, IP address, or URL)
        resolved: DNS resolution data (IPs, MX, NS, TXT records)
        whois: WHOIS registration information
        network: Network and geolocation data
        risk: Threat intelligence and risk scoring
        raw: Original provider response (preserved for debugging/advanced use)
    """

    source: str
    type: str  # "domain", "ip", "url"
    target: str
    resolved: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "ip": [],
            "mx": [],
            "ns": [],
            "txt": [],
        }
    )
    whois: Dict[str, Any] = field(
        default_factory=lambda: {
            "registrar": None,
            "org": None,
            "country": None,
            "emails": [],
            "created": None,
            "updated": None,
            "expires": None,
        }
    )
    network: Dict[str, Optional[str]] = field(
        default_factory=lambda: {
            "asn": None,
            "asn_name": None,
            "isp": None,
            "city": None,
            "region": None,
            "country": None,
        }
    )
    risk: Dict[str, Any] = field(
        default_factory=lambda: {
            "score": None,
            "categories": [],
            "malicious": False,
        }
    )
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert UnifiedRecord to dictionary"""
        return asdict(self)

    def __repr__(self) -> str:
        return f"UnifiedRecord(source={self.source!r}, type={self.type!r}, " f"target={self.target!r})"


def create_empty_record(source: str, target: str, target_type: str) -> UnifiedRecord:
    """
    Create an empty UnifiedRecord with default values.

    Args:
        source: Provider name
        target: Target being enriched
        target_type: Type of target ("domain", "ip", "url")

    Returns:
        UnifiedRecord with all fields initialized to defaults
    """
    return UnifiedRecord(
        source=source,
        type=target_type,
        target=target,
    )


def validate_record(record: UnifiedRecord) -> bool:
    """
    Validate that a UnifiedRecord has all required fields.

    Args:
        record: The UnifiedRecord to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["source", "type", "target"]

    for field_name in required_fields:
        if not getattr(record, field_name, None):
            return False

    # Validate type field
    if record.type not in ["domain", "ip", "url"]:
        return False

    # Validate resolved structure
    if not isinstance(record.resolved, dict):
        return False

    required_resolved_keys = ["ip", "mx", "ns", "txt"]
    for key in required_resolved_keys:
        if key not in record.resolved or not isinstance(record.resolved[key], list):
            return False

    # Validate whois structure
    if not isinstance(record.whois, dict):
        return False

    required_whois_keys = ["registrar", "org", "country", "emails", "created", "updated", "expires"]
    for key in required_whois_keys:
        if key not in record.whois:
            return False

    # Validate network structure
    if not isinstance(record.network, dict):
        return False

    required_network_keys = ["asn", "asn_name", "isp", "city", "region", "country"]
    for key in required_network_keys:
        if key not in record.network:
            return False

    # Validate risk structure
    if not isinstance(record.risk, dict):
        return False

    required_risk_keys = ["score", "categories", "malicious"]
    for key in required_risk_keys:
        if key not in record.risk:
            return False

    return True
