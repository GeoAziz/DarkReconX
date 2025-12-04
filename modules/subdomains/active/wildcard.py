import random
import socket
import string

import aiodns


async def detect_wildcard(domain, tries=3):
    resolver = aiodns.DNSResolver()
    wildcard_ips = set()
    for _ in range(tries):
        gibberish = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        sub = f"{gibberish}.{domain}"
        try:
            ans = await resolver.gethostbyname(sub, socket.AF_INET)
            for ip in ans.addresses:
                wildcard_ips.add(ip)
        except Exception:
            continue
    return wildcard_ips


def filter_wildcards(results, wildcard_ips):
    filtered = []
    for r in results:
        if r and isinstance(r, tuple):
            sub, ips = r
            if not set(ips) & wildcard_ips:
                filtered.append(r)
    return filtered
