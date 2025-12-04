import aiohttp

API_URL = "https://urlscan.io/api/v1/search/?q=domain:{}"


async def get_subdomains(domain: str) -> list:
    subs = set()
    url = API_URL.format(domain)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                for r in data.get("results", []):
                    page = r.get("page", {})
                    host = page.get("domain")
                    if host and host.endswith(domain):
                        subs.add(host)
    return list(subs)
