import asyncio
import socket

import aiodns


async def resolve_subdomain(sub):
    resolver = aiodns.DNSResolver()
    try:
        ans = await resolver.gethostbyname(sub, socket.AF_INET)
        return sub, ans.addresses
    except Exception:
        return None


async def brute_force(domain, wordlist, concurrency=200):
    sem = asyncio.Semaphore(concurrency)

    async def runner(sub):
        async with sem:
            return await resolve_subdomain(sub)

    tasks = []
    for w in wordlist:
        sub = f"{w.strip()}.{domain}"
        tasks.append(runner(sub))
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]
