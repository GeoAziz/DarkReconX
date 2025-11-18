"""Prototype async subdomain enumerator using dnspython async resolver.

This is a lightweight prototype. It requires `dnspython` supporting
`dns.asyncresolver` (dnspython >= 2.x). If the environment lacks the
async resolver, instantiating the class will raise ImportError.

The async path focuses on DNS resolution throughput only (no HTTP
verification) and writes results to the same `results/` directory.
"""
import asyncio
from typing import List, Optional
from pathlib import Path
import json
from rich.console import Console

console = Console()


class AsyncSubdomainFinder:
    def __init__(self, domain: str, wordlist: Optional[str] = None, concurrency: int = 100, verbose: bool = False):
        try:
            import dns.asyncresolver as asyncresolver  # type: ignore
        except Exception as e:
            raise ImportError("async resolver not available; install dnspython>=2.0") from e

        self.asyncresolver = asyncresolver
        self.domain = domain
        self.wordlist = wordlist or (Path(__file__).resolve().parents[2] / "config" / "subdomains.txt")
        self.concurrency = int(concurrency)
        self.verbose = bool(verbose)

    async def _resolve_one(self, sem: asyncio.Semaphore, candidate: str) -> Optional[str]:
        fqdn = f"{candidate}.{self.domain}"
        async with sem:
            try:
                answers = await self.asyncresolver.resolve(fqdn, "A")
                if answers:
                    return fqdn
            except Exception:
                return None
        return None

    async def run_async(self) -> List[str]:
        path = Path(self.wordlist)
        if not path.exists():
            console.print(f"[yellow]Wordlist not found: {path} — no checks performed.[/yellow]")
            return []

        candidates = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        sem = asyncio.Semaphore(self.concurrency)
        tasks = [asyncio.create_task(self._resolve_one(sem, c)) for c in candidates]
        results = await asyncio.gather(*tasks)
        found = [r for r in results if r]

        # write results
        project_root = Path(__file__).resolve().parents[2]
        results_dir = project_root / "results"
        results_dir.mkdir(exist_ok=True)
        out_path = results_dir / f"results_{self.domain}_async.txt"
        out_path.write_text("\n".join(found), encoding="utf-8")
        console.print(f"[green]Async enumeration complete — {len(found)} found. Saved {out_path}[/green]")
        return found

    def run(self) -> List[str]:
        return asyncio.run(self.run_async())


if __name__ == "__main__":
    f = AsyncSubdomainFinder("example.com")
    f.run()
