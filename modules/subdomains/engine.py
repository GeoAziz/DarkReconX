import asyncio
import json
import os

from modules.subdomains.active.bruteforce import brute_force
from modules.subdomains.active.wildcard import detect_wildcard
from modules.subdomains.passive.aggregator import gather_passive
from modules.subdomains.permutations import generate_permutations


async def validate_subdomains(subdomains, concurrency=200):
    import socket

    import aiodns

    sem = asyncio.Semaphore(concurrency)
    resolver = aiodns.DNSResolver()

    async def runner(sub):
        async with sem:
            try:
                await resolver.gethostbyname(sub, socket.AF_INET)
                return sub
            except Exception:
                return None

    tasks = [runner(s) for s in subdomains]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]


async def subdomain_enum(domain, wordlist=None, vt_api_key=None, mode="full", concurrency=200):
    # Passive
    passive = []
    if mode in ("full", "subs"):
        passive = await gather_passive(domain, vt_api_key)
    # Brute-force
    active = []
    if mode in ("full", "bruteforce") and wordlist:
        active = await brute_force(domain, wordlist, concurrency=concurrency)
    # Permutations
    perms = []
    if mode in ("full", "perms") and (passive or active):
        base = set([r if isinstance(r, str) else r[0] for r in (passive + [a[0] for a in active if a])])
        for sub in base:
            perms.extend(generate_permutations(sub))
    # Merge
    raw = set()
    for s in passive:
        raw.add(s if isinstance(s, str) else s[0])
    for a in active:
        if a:
            raw.add(a[0])
    for p in perms:
        raw.add(p)
    clean = sorted(set(raw))
    # Wildcard detection
    wildcard_ips = set()
    if mode in ("full", "bruteforce") and wordlist:
        wildcard_ips = await detect_wildcard(domain)
    # Validate
    validated = await validate_subdomains(clean, concurrency=concurrency)
    # Filter wildcards
    if wildcard_ips:
        validated = [s for s in validated if s not in wildcard_ips]
    # Save
    os.makedirs("results/subdomains", exist_ok=True)
    out = {"domain": domain, "count": len(validated), "subdomains": validated}
    with open(f"results/subdomains/{domain}.json", "w") as f:
        json.dump(out, f, indent=2)
    return out
