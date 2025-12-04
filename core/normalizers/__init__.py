"""
Provider Normalizers for DarkReconX

This package contains normalizer functions for each external provider.
Each normalizer converts provider-specific responses into the unified UnifiedRecord schema.

Available normalizers:
- ipinfo: IPInfo.io API responses
- virustotal: VirusTotal API responses
- whoisxml: WhoisXML API responses
- dns: DNS resolver responses

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from .dns import normalize_dns
from .ipinfo import normalize_ipinfo
from .virustotal import normalize_virustotal
from .whoisxml import normalize_whoisxml

__all__ = [
    "normalize_ipinfo",
    "normalize_virustotal",
    "normalize_whoisxml",
    "normalize_dns",
]
