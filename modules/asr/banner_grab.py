import asyncio

import httpx

BANNER_PORTS = {21: "ftp", 22: "ssh", 25: "smtp", 80: "http", 443: "https", 3306: "mysql", 5432: "postgres"}


async def grab_banner(host, port, timeout=5):
    try:
        if port in (80, 443):
            url = f"{'https' if port == 443 else 'http'}://{host}:{port}"
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                r = await client.head(url)
                banner = r.headers.get("server", "")
                return {
                    "banner": banner,
                    "service": "https" if port == 443 else "http",
                    "product": banner.split("/")[0] if "/" in banner else banner,
                    "version": banner.split("/")[1] if "/" in banner else "",
                }
        else:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
            data = await asyncio.wait_for(reader.read(128), timeout=timeout)
            banner = data.decode(errors="ignore").strip()
            service = BANNER_PORTS.get(port, "")
            product, version = "", ""
            if "/" in banner:
                product, version = banner.split("/", 1)
            elif banner:
                product = banner
            writer.close()
            await writer.wait_closed()
            return {"banner": banner, "service": service, "product": product, "version": version}
    except Exception:
        return {"banner": "", "service": BANNER_PORTS.get(port, ""), "product": "", "version": ""}
