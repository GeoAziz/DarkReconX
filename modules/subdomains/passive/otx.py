import aiohttp

API_URL = "https://otx.alienvault.com/api/v1/indicators/domain/{}/passive_dns"


async def get_subdomains(domain: str) -> list:
    subs = set()
    url = API_URL.format(domain)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                for r in data.get("passive_dns", []):
                    host = r.get("hostname")
                    if host and host.endswith(domain):
                        subs.add(host)
    return list(subs)
