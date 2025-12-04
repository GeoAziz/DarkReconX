import asyncio
import time


async def probe_port(host, port, timeout=3):
    start = time.time()
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        probe_time = int((time.time() - start) * 1000)
        return port, probe_time
    except Exception:
        return None


async def port_probe(host, ports, concurrency=100, timeout=3):
    sem = asyncio.Semaphore(concurrency)

    async def runner(port):
        async with sem:
            return await probe_port(host, port, timeout)

    tasks = [runner(p) for p in ports]
    out = await asyncio.gather(*tasks)
    open_ports = [p for p in out if p]
    return {"open_ports": [p[0] for p in open_ports], "probe_time_ms": sum([p[1] for p in open_ports]) if open_ports else 0}
