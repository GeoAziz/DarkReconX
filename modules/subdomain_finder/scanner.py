import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import dns.resolver
from rich.console import Console

from config.loader import get_config
from core.http_client import HTTPClient
from modules.subdomain_finder import api as api_helpers
from core.output import standard_response

console = Console()


class SubdomainFinder:
    """Fast subdomain enumeration using DNS resolution.

    This class uses a thread pool to resolve candidate subdomains concurrently
    and writes results to a file `results_<domain>.txt` in the current
    working directory.
    """

    def __init__(
        self,
        domain: str,
        wordlist: Optional[str] = None,
        use_tor: Optional[bool] = None,
        workers: Optional[int] = None,
        verify_http: bool = False,
        verify_timeout: int = 10,
        verify_retries: int = 2,
        verify_backoff: float = 0.5,
        verbose: bool = False,
    ):
        self.domain = domain.strip()
        if not self.domain:
            raise ValueError("domain must be provided")

        # default wordlist under config/
        self.wordlist = wordlist or (Path(__file__).resolve().parents[2] / "config" / "subdomains.txt")

        cfg = get_config().config if hasattr(get_config(), "config") else {}
        self.use_tor = cfg.get("tor", {}).get("enabled", False) if use_tor is None else bool(use_tor)
        self.http = HTTPClient(use_tor=self.use_tor, verbose=verbose)
        self.verify_http = bool(verify_http)
        self.verify_timeout = int(verify_timeout)
        self.verify_retries = int(verify_retries)
        self.verify_backoff = float(verify_backoff)
        self.verbose = bool(verbose)

        # API integration fields (set via CLI or programmatically)
        self.api_name: Optional[str] = None
        self.api_key: Optional[str] = None

        # threads/worker count for concurrency
        if workers is None:
            # default: min(32, (cpu_count * 5) or 10)
            try:
                cpu = os.cpu_count() or 2
                self.workers = min(32, cpu * 5)
            except Exception:
                self.workers = 10
        else:
            self.workers = int(workers)

    def resolve(self, subdomain: str) -> Optional[str]:
        try:
            full_domain = f"{subdomain}.{self.domain}"
            answers = dns.resolver.resolve(full_domain, "A")
            if answers:
                return full_domain
            return None
        except Exception:
            return None

    def set_api(self, name: str, api_key: Optional[str]):
        """Configure an API integration for enrichment.

        name: one of 'virustotal'|'vt'|'securitytrails'
        api_key: key string for the chosen API
        """
        if not name:
            self.api_name = None
            self.api_key = None
            return
        self.api_name = name.lower()
        self.api_key = api_key
        # whether to use the cache for enrichment (can be overridden by env API_CACHE_BYPASS)
        self.api_use_cache = True

    def set_api_cache(self, use_cache: bool):
        """Explicitly control whether enrichment should use cached responses."""
        self.api_use_cache = bool(use_cache)

    def set_api_refresh(self, refresh: bool):
        """If True, force refresh API responses and update the cache."""
        self.api_force_refresh = bool(refresh)

    def run(self) -> dict:
        console.print(f"[bold cyan]Starting subdomain enumeration on {self.domain} (workers={self.workers})[/bold cyan]")
        found: List[str] = []
        wl_path = Path(self.wordlist)
        if not wl_path.exists():
            console.print(f"[yellow]Wordlist not found: {wl_path} — no checks performed.[/yellow]")
            data = {"domain": self.domain, "count": 0, "subdomains": []}
            return standard_response("subdomain_finder", data=data)

        # gather candidates
        candidates = [
            line.strip() for line in wl_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()
        ]

        # use ThreadPoolExecutor to resolve concurrently
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(self.resolve, sub): sub for sub in candidates}
            for fut in as_completed(futures):
                res = fut.result()
                if not res:
                    continue

                skipped = False
                # optionally perform HTTP HEAD verification with retries/backoff
                if self.verify_http:
                    url_https = f"https://{res}"
                    url_http = f"http://{res}"
                    code = None
                    for attempt in range(self.verify_retries + 1):
                        # try https then http
                        code = self.http.head(url_https, timeout=self.verify_timeout)
                        if code is None:
                            code = self.http.head(url_http, timeout=self.verify_timeout)

                        if code is not None and code < 400:
                            break

                        # if not last attempt, sleep with exponential backoff
                        if attempt < self.verify_retries:
                            sleep_for = self.verify_backoff * (2**attempt)
                            if self.verbose:
                                console.print(
                                    f"[blue]Verify attempt {attempt+1} failed for {res}; sleeping {sleep_for}s before retry[/blue]"
                                )
                            time.sleep(sleep_for)

                    if code is None or code >= 400:
                        console.print(f"[yellow]- Skipped (no HTTP response): {res}[/yellow]")
                        skipped = True

                if skipped:
                    # accumulate skipped results for later analysis
                    if not hasattr(self, "skipped"):
                        self.skipped = []
                    self.skipped.append(res)
                    continue

                console.print(f"[green]+ Found: {res}[/green]")
                found.append(res)

        # Save results to results/ under project root (caller may override)
        project_root = Path(__file__).resolve().parents[2]
        results_dir = project_root / "results"
        results_dir.mkdir(exist_ok=True)
        out_path = results_dir / f"results_{self.domain}.txt"
        with out_path.open("w", encoding="utf-8") as fh:
            for d in found:
                fh.write(d + "\n")
        # Also return list for caller to persist in other formats

        console.print(f"[bold yellow]Enumeration complete! Found {len(found)} subdomains[/bold yellow]")
        # If an API integration is configured, enrich results (cached)
        if self.api_name and self.api_key:
            try:
                enriched = {}
                for d in found:
                    res = None
                    if self.api_name in ("virustotal", "vt"):
                        res = api_helpers.enrich_with_virustotal(
                            d,
                            self.api_key,
                            use_cache=self.api_use_cache if hasattr(self, "api_use_cache") else True,
                            ttl=3600,
                            force_refresh=getattr(self, "api_force_refresh", False),
                        )
                    elif self.api_name in ("dnsdb",):
                        res = api_helpers.enrich_with_dnsdb(
                            d,
                            self.api_key,
                            use_cache=self.api_use_cache if hasattr(self, "api_use_cache") else True,
                            ttl=3600,
                            force_refresh=getattr(self, "api_force_refresh", False),
                        )
                    elif self.api_name in ("whoisxml", "whois"):
                        res = api_helpers.enrich_with_whoisxml(
                            d,
                            self.api_key,
                            use_cache=self.api_use_cache if hasattr(self, "api_use_cache") else True,
                            ttl=3600,
                            force_refresh=getattr(self, "api_force_refresh", False),
                        )
                    elif self.api_name in ("ipinfo",):
                        # ipinfo expects IP address; try resolving first (best-effort)
                        try:
                            import socket

                            ip = socket.gethostbyname(d)
                            res = api_helpers.enrich_with_ipinfo(
                                ip,
                                self.api_key,
                                use_cache=self.api_use_cache if hasattr(self, "api_use_cache") else True,
                                ttl=3600,
                                force_refresh=getattr(self, "api_force_refresh", False),
                            )
                        except Exception:
                            res = {"error": "resolve_failed", "domain": d}
                    else:
                        res = {"error": "unknown_api", "api": self.api_name}

                    enriched[d] = res

                enrich_path = results_dir / f"results_{self.domain}_enriched.json"
                enrich_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
                console.print(f"[bold magenta]Enrichment complete — saved {enrich_path}[/bold magenta]")
            except Exception as e:
                console.print(f"[red]Enrichment failed: {e}[/red]")

        # Save skipped results separately for later analysis
        if hasattr(self, "skipped") and self.skipped:
            skip_path = Path.cwd() / f"skipped_results_{self.domain}.txt"
            with skip_path.open("w", encoding="utf-8") as sf:
                for s in self.skipped:
                    sf.write(s + "\n")

        # Build normalized data
        data = {
            "domain": self.domain,
            "count": len(found),
            "subdomains": found,
        }
        return standard_response("subdomain_finder", data=data)


if __name__ == "__main__":
    # quick manual test
    s = SubdomainFinder("example.com")
    s.run()
