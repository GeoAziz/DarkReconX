import re

import httpx


async def web_fingerprint(host, port=80, timeout=5):
    url = f"http://{host}:{port}" if port != 443 else f"https://{host}:{port}"
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            r = await client.get(url)
            tech = []
            server_header = r.headers.get("server", "")
            if "nginx" in server_header.lower():
                tech.append("nginx")
            if "apache" in server_header.lower():
                tech.append("apache")
            if "express" in r.text.lower():
                tech.append("express")
            if "react" in r.text.lower():
                tech.append("react")
            title = ""
            m = re.search(r"<title>(.*?)</title>", r.text, re.IGNORECASE)
            if m:
                title = m.group(1)
            return {"status": r.status_code, "title": title, "tech": tech, "server_header": server_header}
    except Exception:
        return {}
