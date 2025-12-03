"""Prototype async subdomain enumerator using dnspython async resolver.

This is a lightweight prototype. It requires `dnspython` supporting
`dns.asyncresolver` (dnspython >= 2.x). If the environment lacks the
async resolver, instantiating the class will raise ImportError.

The async path supports both DNS resolution and optional HTTP verification
using httpx.AsyncClient, and writes results to the same `results/` directory.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

console = Console()


class AsyncSubdomainFinder:
    def __init__(
        self,
        domain: str,
        wordlist: Optional[str] = None,
        concurrency: int = 100,
        verbose: bool = False,
        verify_http: bool = False,
        http_timeout: float = 5.0,
    ):
        try:
            import dns.asyncresolver as asyncresolver  # type: ignore
        except Exception as e:
            raise ImportError("async resolver not available; install dnspython>=2.0") from e

        self.asyncresolver = asyncresolver
        self.domain = domain
        self.wordlist = wordlist or (Path(__file__).resolve().parents[2] / "config" / "subdomains.txt")
        self.concurrency = int(concurrency)
        self.verbose = bool(verbose)
        self.verify_http = verify_http
        self.http_timeout = http_timeout

    async def _resolve_one(self, sem: asyncio.Semaphore, candidate: str) -> Optional[Dict[str, str]]:
        """Resolve a single subdomain candidate via async DNS.

        Returns:
            Dict with 'fqdn' and optional 'ip' if resolved, None if failed
        """
        fqdn = f"{candidate}.{self.domain}"
        async with sem:
            try:
                answers = await self.asyncresolver.resolve(fqdn, "A")
                if answers:
                    # Pick first IP for simplicity
                    ip = str(answers[0])
                    return {"fqdn": fqdn, "ip": ip}
            except Exception:
                return None
        return None

    async def _verify_http_one(self, client, sem: asyncio.Semaphore, result: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Optionally verify HTTP reachability of a resolved subdomain.

        Args:
            client: httpx.AsyncClient instance
            sem: asyncio.Semaphore for concurrency control
            result: Dict with 'fqdn' and 'ip' from DNS resolution

        Returns:
            Updated result dict with 'http_status' if reachable, None if unreachable
        """
        fqdn = result["fqdn"]
        async with sem:
            for scheme in ["https", "http"]:
                try:
                    url = f"{scheme}://{fqdn}"
                    resp = await client.head(url, timeout=self.http_timeout, follow_redirects=True)
                    result["http_status"] = resp.status_code
                    result["http_scheme"] = scheme
                    return result
                except Exception:
                    continue
        # If no scheme worked, return None to mark unreachable
        return None

    async def run_async(self) -> List[Dict[str, str]]:
        """Run async subdomain enumeration with optional HTTP verification.

        Returns:
            List of dicts with subdomain details (fqdn, ip, http_status if verified)
        """
        path = Path(self.wordlist)
        if not path.exists():
            console.print(f"[yellow]Wordlist not found: {path} — no checks performed.[/yellow]")
            return []

        candidates = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]

        # Phase 1: DNS resolution
        sem = asyncio.Semaphore(self.concurrency)
        tasks = [asyncio.create_task(self._resolve_one(sem, c)) for c in candidates]
        results = await asyncio.gather(*tasks)
        found = [r for r in results if r]

        if self.verbose:
            console.print(f"[cyan]DNS resolution: {len(found)} subdomains resolved[/cyan]")

        # Phase 2: Optional HTTP verification
        if self.verify_http and found:
            try:
                import httpx
            except ImportError:
                console.print("[yellow]httpx not available; skipping HTTP verification[/yellow]")
            else:
                if self.verbose:
                    console.print(f"[cyan]Starting HTTP verification for {len(found)} subdomains...[/cyan]")

                async with httpx.AsyncClient(verify=False) as client:
                    http_sem = asyncio.Semaphore(self.concurrency)
                    http_tasks = [asyncio.create_task(self._verify_http_one(client, http_sem, r)) for r in found]
                    verified_results = await asyncio.gather(*http_tasks)
                    found = [r for r in verified_results if r]

                if self.verbose:
                    console.print(f"[cyan]HTTP verification: {len(found)} subdomains reachable[/cyan]")

        # Write results
        project_root = Path(__file__).resolve().parents[2]
        results_dir = project_root / "results"
        results_dir.mkdir(exist_ok=True)

        # Write both text and JSON
        out_txt = results_dir / f"results_{self.domain}_async.txt"
        out_json = results_dir / f"results_{self.domain}_async.json"

        txt_lines = []
        for r in found:
            line = r["fqdn"]
            if "http_status" in r:
                line += f" [{r['http_scheme']}:{r['http_status']}]"
            txt_lines.append(line)

        out_txt.write_text("\n".join(txt_lines), encoding="utf-8")
        out_json.write_text(json.dumps(found, indent=2), encoding="utf-8")

        console.print(f"[green]Async enumeration complete — {len(found)} found. Saved {out_txt} and {out_json}[/green]")
        return found

    def run(self) -> List[Dict[str, str]]:
        """Synchronous wrapper for run_async."""
        return asyncio.run(self.run_async())


if __name__ == "__main__":
    f = AsyncSubdomainFinder("example.com", verify_http=True, verbose=True)
    f.run()
