import aiohttp

API_URL = "http://web.archive.org/cdx/search/cdx?url=*.{}&output=json&fl=original&collapse=urlkey"


async def get_subdomains(domain: str) -> list:
    subs = set()
    url = API_URL.format(domain)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json(content_type=None)
                    for row in data[1:]:
                        url = row[0]
                        host = url.split("/")[2] if "/" in url else url
                        if host.endswith(domain):
                            subs.add(host)
                except Exception:
                    pass
    return list(subs)
