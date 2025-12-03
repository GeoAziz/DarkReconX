# Contributing Modules to DarkReconX

This guide explains how to create new scanner modules that integrate with the DarkReconX framework.

## Table of Contents

- [Module Architecture Contract](#module-architecture-contract)
- [Minimal Implementation](#minimal-implementation)
- [Contract Details](#contract-details)
- [Example Modules](#example-modules)
- [Testing Your Module](#testing-your-module)
- [Deployment Checklist](#deployment-checklist)

## Module Architecture Contract

Every module must follow this contract to be compatible with DarkReconX:

### Required Structure

```
modules/your_module_name/
├── __init__.py          # Import scanner.py
├── scanner.py           # Main implementation (required)
└── api.py               # Optional: Provider-specific helpers
```

## Minimal Implementation

```python
# modules/your_module_name/scanner.py
from typing import Optional, Dict
from rich.console import Console

console = Console()

class YourModule:
    """Module description for help text."""
    
    description = "Brief one-line description of what this module does"
    
    def __init__(self, verbose: bool = False):
        """Initialize module.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
    
    def run(self, target: str) -> Dict:
        """Execute module logic.
        
        Args:
            target: The target to scan (domain, IP, username, etc.)
            
        Returns:
            Dictionary with results or error information
        """
        try:
            console.print(f"[cyan]Scanning {target}...[/cyan]")
            
            # Your implementation here
            results = self.fetch(target)
            normalized = self.normalize(results)
            
            return {
                "success": True,
                "target": target,
                "data": normalized,
            }
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return {
                "success": False,
                "target": target,
                "error": str(e),
            }
    
    def fetch(self, target: str) -> Dict:
        """Fetch raw data from provider.
        
        Args:
            target: The target to query
            
        Returns:
            Raw API response as dictionary
        """
        pass
    
    def normalize(self, raw: Dict) -> Dict:
        """Normalize provider response to common schema.
        
        Args:
            raw: Raw provider response
            
        Returns:
            Normalized data with consistent schema
        """
        pass
```

## Contract Details

### 1. Class Name & Location

- Place scanner in `modules/<module_name>/scanner.py`
- Class name: CamelCase, e.g., `SubdomainFinder`, `WhoisModule`, `UsernameRecon`
- Importable as: `from modules.your_module.scanner import YourModule`

### 2. Class Attributes

```python
class YourModule:
    description: str = "One-line description shown in list command"
```

### 3. Main Method (`run()`)

```python
def run(self, target: str) -> Dict:
    """Main execution method.
    
    Args:
        target: Domain, IP, username, or other target
        
    Returns:
        Dictionary with:
        {
            "success": bool,
            "target": str,
            "data": {...},  # Your results
            "error": str,   # If success=False
            "cached": bool, # Optional: indicate if from cache
        }
    """
```

### 4. Normalized Output Schema

Return consistent data structure:

```python
{
    "success": True,
    "target": "example.com",
    "data": {
        "provider": "module_name",
        "hostname": "...",
        "ip": "...",
        "asn": "...",
        "registrar": "...",
        "registrant": "...",
        "location": {
            "country": "...",
            "city": "...",
        },
        "additional_field": "...",
        "raw": {...},
    }
}
```

### 5. Error Handling

Always return structured errors:

```python
return {
    "success": False,
    "target": target,
    "error": "Descriptive error message",
}
```

## Example Modules

### Example 1: WHOIS Lookup Module

```python
# modules/whois_lookup/scanner.py
from typing import Dict
import whois
from rich.console import Console

console = Console()

class WhoisModule:
    description = "WHOIS domain lookup and registrar information"
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def run(self, domain: str) -> Dict:
        """Lookup WHOIS information for domain."""
        try:
            console.print(f"[cyan]Looking up WHOIS for {domain}...[/cyan]")
            raw = self.fetch(domain)
            normalized = self.normalize(raw)
            
            return {
                "success": True,
                "target": domain,
                "data": normalized,
            }
        except Exception as e:
            return {
                "success": False,
                "target": domain,
                "error": str(e),
            }
    
    def fetch(self, domain: str) -> Dict:
        """Fetch raw WHOIS data."""
        response = whois.whois(domain)
        return response
    
    def normalize(self, raw: Dict) -> Dict:
        """Normalize WHOIS response."""
        return {
            "provider": "whois",
            "domain": raw.get("domain"),
            "registrar": raw.get("registrar"),
            "registrant": raw.get("registrant_name"),
            "created": str(raw.get("creation_date")),
            "expires": str(raw.get("expiration_date")),
            "nameservers": raw.get("name_servers", []),
        }
```

### Example 2: API-Based Module with Caching

```python
# modules/github_users/scanner.py
from typing import Dict
import requests
from core.cache import get_cached, set_cached
from rich.console import Console

console = Console()

class GithubUsers:
    description = "GitHub user reconnaissance"
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def run(self, username: str) -> Dict:
        """Lookup GitHub user information."""
        try:
            # Check cache
            cache_key = f"github:user:{username}"
            cached = get_cached(cache_key, max_age=86400)
            if cached is not None:
                return {
                    "success": True,
                    "target": username,
                    "data": cached,
                    "cached": True,
                }
            
            # Fetch from API
            raw = self.fetch(username)
            normalized = self.normalize(raw)
            
            # Cache results
            set_cached(cache_key, normalized)
            
            return {
                "success": True,
                "target": username,
                "data": normalized,
                "cached": False,
            }
        except Exception as e:
            return {
                "success": False,
                "target": username,
                "error": str(e),
            }
    
    def fetch(self, username: str) -> Dict:
        """Fetch from GitHub API."""
        url = f"https://api.github.com/users/{username}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    
    def normalize(self, raw: Dict) -> Dict:
        """Normalize GitHub API response."""
        return {
            "provider": "github",
            "username": raw.get("login"),
            "name": raw.get("name"),
            "bio": raw.get("bio"),
            "company": raw.get("company"),
            "location": raw.get("location"),
            "followers": raw.get("followers"),
            "following": raw.get("following"),
            "url": raw.get("html_url"),
        }
```

## Testing Your Module

### Unit Tests

```python
# tests/test_your_module.py
import pytest
from unittest.mock import patch, MagicMock
from modules.your_module.scanner import YourModule

def test_module_run_success():
    """Test successful module execution."""
    module = YourModule(verbose=False)
    
    with patch("modules.your_module.scanner.YourModule.fetch") as mock_fetch:
        mock_fetch.return_value = {"field": "value"}
        result = module.run("example.com")
    
    assert result["success"] is True
    assert result["target"] == "example.com"
    assert "data" in result

def test_module_error_handling():
    """Test error handling."""
    module = YourModule(verbose=False)
    
    with patch("modules.your_module.scanner.YourModule.fetch") as mock_fetch:
        mock_fetch.side_effect = Exception("API Error")
        result = module.run("example.com")
    
    assert result["success"] is False
    assert "error" in result
```

### Integration Tests (Optional)

```python
import pytest
import os

@pytest.mark.integration
def test_real_api_call():
    """Integration test - only runs with RUN_API_INTEGRATION=1."""
    if not os.getenv("RUN_API_INTEGRATION"):
        pytest.skip("Integration tests disabled")
    
    module = YourModule()
    result = module.run("example.com")
    assert result["success"] is True
```

## CLI Integration

Once your module is created, it's automatically discoverable:

```bash
# List available modules
python -m cli.main list

# Run your module
python -m cli.main run your_module --target example.com

# With verbose output
python -m cli.main run your_module --target example.com --verbose
```

## API Provider Integrations

Create `api.py` for provider-specific helpers:

```python
# modules/your_module/api.py
from typing import Dict, Optional
from core.cache import get_cached, set_cached
import requests

def enrich_with_provider(domain: str, api_key: str, use_cache: bool = True) -> Dict:
    """Fetch and cache provider data."""
    cache_key = f"provider:domain:{domain}"
    
    if use_cache:
        cached = get_cached(cache_key)
        if cached:
            return {"from_cache": True, "data": cached}
    
    # API call
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(f"https://api.provider.com/domain/{domain}",
                        headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    
    # Cache
    set_cached(cache_key, data)
    
    return {"from_cache": False, "data": data}
```

## Tor Support

```python
class MyModule:
    def __init__(self, use_tor: Optional[bool] = None, verbose: bool = False):
        from core.http_client import HTTPClient
        
        self.use_tor = use_tor or False
        self.verbose = verbose
        self.http = HTTPClient(use_tor=self.use_tor, verbose=verbose)
    
    def fetch(self, target: str):
        # HTTP requests go through self.http
        return self.http.get(f"https://api.example.com/{target}")
```

## Deployment Checklist

Before submitting your module:

- [ ] Module lives in `modules/module_name/scanner.py`
- [ ] Class has `description` attribute
- [ ] `run(target: str)` method implemented
- [ ] Returns `Dict` with `success`, `target`, and `data` or `error`
- [ ] All public functions have type hints and docstrings
- [ ] Unit tests added to `tests/test_module_name.py`
- [ ] Tests mock external API calls (no real network in CI)
- [ ] Code passes linting: `make lint`
- [ ] Code is formatted: `make fmt`
- [ ] All tests pass: `make test`
- [ ] No hardcoded credentials
- [ ] Uses `.env` or config for sensitive data
- [ ] Error handling implemented
- [ ] Logging added for debugging

## Best Practices

### Import-Time Safety

⚠️ **CRITICAL:** Do NOT perform network I/O or heavy work in `__init__`

```python
# ❌ WRONG - This fails CI!
class BadModule:
    def __init__(self):
        self.data = requests.get("https://api.example.com").json()

# ✅ CORRECT - Network access only in run()
class GoodModule:
    def __init__(self):
        self.api_url = "https://api.example.com"
    
    def run(self, target: str):
        data = requests.get(self.api_url).json()
        return {"success": True, "data": data}
```

### Caching Pattern

```python
def run(self, target: str) -> Dict:
    cache_key = f"module:target:{target}"
    
    # Check cache first
    cached = get_cached(cache_key, max_age=3600)
    if cached:
        return {"success": True, "target": target, "data": cached, "cached": True}
    
    # Fetch fresh data
    try:
        data = self.fetch(target)
        set_cached(cache_key, data)
        return {"success": True, "target": target, "data": data, "cached": False}
    except Exception as e:
        return {"success": False, "target": target, "error": str(e)}
```

### API Key Handling

```python
import os
from config.loader import get_config

def run(self, target: str) -> Dict:
    # Prefer config system over direct os.getenv
    cfg = get_config().config
    api_key = cfg.get("my_provider", {}).get("api_key")
    
    if not api_key:
        return {"success": False, "error": "Missing API key"}
    
    # Use API key
    ...
```

## Common Providers

Recommended OSINT providers for integration:

- **VirusTotal** - Domains, IPs, DNS, WHOIS
- **DNSDB Scout** - Passive DNS records
- **Certificate Transparency** - Domain enumeration via SSL certs
- **WhoisXML** - WHOIS lookups and data
- **ipinfo.io** - IP geolocation and ASN
- **GitHub API** - User and repository reconnaissance
- **Shodan** - Internet-connected device search
- **Censys** - Certificate and host data

## Questions?

- Review existing modules in `modules/` for examples
- Check `CONTRIBUTING.md` for general contribution guidelines
- Open an issue to discuss module ideas before implementing

Thank you for extending DarkReconX! 🎉
