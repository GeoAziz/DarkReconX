import httpx

ADMIN_PATHS = ["/admin", "/login", "/wp-admin", "/dashboard", "/manager/html"]


async def admin_path_scan(host, port=80, timeout=5, safe_mode=True):
    url_base = f"http://{host}:{port}" if port != 443 else f"https://{host}:{port}"
    results = []
    if safe_mode:
        method = "HEAD"
    else:
        method = "GET"
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        for path in ADMIN_PATHS:
            try:
                r = await client.request(method, url_base + path)
                results.append({"path": path, "status": r.status_code})
            except Exception:
                results.append({"path": path, "status": None})
    return {"paths": results}
