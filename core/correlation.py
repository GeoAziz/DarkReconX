from collections import defaultdict
from typing import Any, Dict, List, Tuple, Mapping


def correlate_domains_by_ip(profile: Mapping[str, List[Any]]) -> List[Tuple[str, List[str], float]]:
    """Given a profile dict containing 'domains' and 'ips' mappings, find domains sharing IPs.

    Returns a list of tuples: (ip, [domains], confidence)
    """
    # Build reverse mapping ip -> domains
    ip_to_domains = defaultdict(list)
    domains = profile.get("domains", [])
    # domains entries may be simple strings or dicts with 'ip'
    for d in domains:
        if isinstance(d, dict):
            ip = d.get("ip")
            if ip:
                ip_to_domains[ip].append(d.get("domain") or d.get("name") or "")
        elif isinstance(d, str):
            # no ip info
            continue

    results = []
    for ip, doms in ip_to_domains.items():
        if len(doms) > 1:
            # confidence increases with number of domains sharing the same IP
            confidence = min(0.9, 0.4 + 0.1 * (len(doms) - 1))
            results.append((ip, doms, confidence))

    return results


def detect_shared_asn(profile: Mapping[str, List[Any]]) -> List[Tuple[str, List[str], float]]:
    """Detect domains sharing the same ASN from network records.

    Returns list of tuples (asn, domains, confidence)
    """
    asn_to_domains = defaultdict(list)
    domains = profile.get("domains", [])
    for d in domains:
        if isinstance(d, dict):
            asn = d.get("asn")
            if asn:
                asn_to_domains[asn].append(d.get("domain") or d.get("name") or "")

    res = []
    for asn, doms in asn_to_domains.items():
        if len(doms) > 1:
            confidence = min(0.9, 0.3 + 0.05 * (len(doms) - 1))
            res.append((asn, doms, confidence))

    return res
