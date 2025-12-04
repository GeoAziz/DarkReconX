# DarkReconX v1.0 Team Onboarding Guide

Welcome to DarkReconX! This guide will help you get up to speed quickly and contribute effectively.

## 📋 Table of Contents

1. [Getting Started (5 min)](#getting-started)
2. [Project Structure (10 min)](#project-structure)
3. [Running Your First Scan (10 min)](#running-your-first-scan)
4. [Understanding the Architecture (20 min)](#architecture)
5. [Common Tasks (15 min)](#common-tasks)
6. [Adding New Providers (30 min)](#adding-providers)
7. [Testing & Quality (15 min)](#testing--quality)
8. [Troubleshooting (10 min)](#troubleshooting)

---

## ✅ Getting Started

### 1. Clone & Setup (5 minutes)

```bash
# Clone repository
git clone https://github.com/GeoAziz/DarkReconX.git
cd DarkReconX

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate

# Install development dependencies
pip install -e ".[dev]"

# Verify installation (should show 51 passed)
pytest tests/ -v

# Check code quality (should show ~0 errors)
flake8 .
```

### 2. Configure API Keys (3 minutes)

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Need keys?** See provider links in README.md section "Providers"

### 3. Run First Scan (2 minutes)

```bash
# Basic scan
darkreconx pipeline --targets example.com

# Check results
cat results/pipeline/summary.json
```

**Success!** You should see JSON output with data from available providers.

---

## 📁 Project Structure

```
DarkReconX/
├── cli/                      # CLI interface (Typer)
│   ├── main.py              # Entry point, all commands
│   └── helpers.py           # Rich formatting utilities
│
├── core/                     # Core framework
│   ├── orchestrator.py       # Async provider orchestration (50 workers)
│   ├── cache.py             # File-based caching (24h TTL)
│   ├── rate_limit.py        # Token bucket rate limiting
│   ├── retry.py             # Exponential backoff (3 attempts)
│   ├── module.py            # BaseModule class
│   ├── errors.py            # Custom exceptions
│   └── normalizers/         # Per-provider result normalization
│
├── modules/                  # Provider modules
│   ├── dnsdb/               # DNSDB passive DNS (core)
│   ├── ipinfo/              # IP geolocation (core)
│   ├── whoisxml/            # WHOIS data (core)
│   ├── virustotal/          # Threat intelligence (optional)
│   ├── shodan/              # Port scanning (optional)
│   └── censys/              # Certificate data (optional)
│
├── config/                   # Configuration
│   ├── loader.py            # .env and env var loading
│   ├── default.yml          # Default settings
│   └── subdomains.txt       # Wordlist (for subdomain finder)
│
├── tests/                    # Test suite (51 tests, 100% passing)
│   ├── test_orchestrator.py
│   ├── test_cache_*.py
│   ├── test_rate_limit.py
│   ├── test_async_scanner.py
│   └── ... (18 more test files)
│
├── results/                  # Output directory (git-ignored)
│   └── pipeline/            # Pipeline results
│
├── docs/                     # Documentation
│   ├── ONBOARDING.md        # This file
│   ├── ARCHITECTURE.md      # Deep technical dive
│   ├── PROVIDERS_GUIDE.md   # Provider setup details
│   └── roadmap.md           # v1.1+ plans
│
├── README.md                # Main documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── CONTRIBUTING_MODULES.md  # Provider extension guide
├── requirements.txt         # Pinned dependencies (21 packages)
├── pyproject.toml          # Project metadata
├── setup.py                # Package distribution config
├── Makefile                # Common commands
└── .env.example            # Configuration template
```

### Key Files You'll Edit

| File | Purpose | Frequency |
|------|---------|-----------|
| `cli/main.py` | Add CLI commands | Weekly |
| `core/orchestrator.py` | Adjust provider logic | Monthly |
| `modules/*/scanner.py` | Add/modify providers | Daily |
| `core/normalizers/` | Fix provider response parsing | As needed |
| `tests/test_*.py` | Add test coverage | Daily |

---

## 🚀 Running Your First Scan

### Basic Reconnaissance

```bash
# Single target
darkreconx pipeline --targets example.com

# Multiple targets
darkreconx pipeline --targets "example.com,google.com,github.com"

# From file (one per line)
echo "example.com" > targets.txt
darkreconx pipeline --targets targets.txt
```

### Advanced Usage

```bash
# Specific providers only
darkreconx pipeline --targets example.com --providers dns,virustotal

# Force fresh data (skip cache)
darkreconx pipeline --targets example.com --no-cache

# Reduce workers for slow network
darkreconx pipeline --targets example.com --max-workers 10

# Save to custom directory
darkreconx pipeline --targets example.com --outdir results/custom_scan

# Export as CSV
darkreconx pipeline --targets example.com --format csv
```

### Understanding Results

```bash
# JSON summary with all provider data
cat results/pipeline/summary.json

# Human-readable text version
cat results/pipeline/summary.txt

# Interactive HTML dashboard
open results/pipeline/report.html  # macOS
xdg-open results/pipeline/report.html  # Linux
```

### Performance Tips

- **Cache is your friend**: 70-90% of queries hit cache (no API calls!)
- **Batch processing**: Process 100 targets at once for efficiency
- **Workers**: Default 50 is good; reduce to 10-20 on slow networks
- **Providers**: Use `--providers` to skip expensive/slow ones

---

## 🏗️ Architecture

### High-Level Flow

```
User Input (CLI) 
    ↓
Load Configuration (.env, env vars)
    ↓
Initialize Providers (DNSDB, WhoisXML, IPinfo, etc.)
    ↓
Load Target List
    ↓
FOR EACH TARGET:
    ├─ Check Cache (24h TTL)
    ├─ If cached: Return cached data
    ├─ If not cached:
    │   ├─ Apply Rate Limiting (Token Bucket)
    │   ├─ Execute async calls to ALL providers (50 concurrent)
    │   ├─ Retry failed requests (3 attempts, exponential backoff)
    │   └─ Normalize provider responses to unified schema
    ├─ Cache results
    └─ Merge provider data
    ↓
Generate Reports (JSON, CSV, HTML)
    ↓
Save to results/ directory
    ↓
Done!
```

### Key Concepts

#### 1. **Async Orchestration**
- All providers run in parallel (50 concurrent workers)
- Each provider call is independent
- Missing API key? Provider skipped, pipeline continues
- One slow provider doesn't block others

```python
# In core/orchestrator.py
results = await asyncio.gather(
    dnsdb_scan(target),
    whoisxml_scan(target),
    ipinfo_scan(target),
    shodan_scan(target),
    censys_scan(target),
    virustotal_scan(target),
    return_exceptions=True  # Don't crash on error
)
```

#### 2. **Intelligent Caching**
- 24-hour TTL (configurable via `DARKRECONX_CACHE_TTL`)
- File-based storage (~/.darkreconx_cache/)
- 70-90% cache hit rate on repeated targets
- Saves API quota and speeds up re-scans

```python
# In core/cache.py
cache_key = f"{target}:{provider}"
cached = read_cache(cache_key)
if cached and not expired:
    return cached  # No API call!
else:
    fresh = fetch_from_provider(target)
    write_cache(cache_key, fresh)
    return fresh
```

#### 3. **Rate Limiting**
- Token bucket algorithm
- Per-provider rate limits respected
- Automatic backoff on 429 responses
- Configurable: `DARKRECONX_RETRY_ATTEMPTS`, `DARKRECONX_TIMEOUT`

```python
# In core/rate_limit.py
if response.status_code == 429:
    wait_time = exponential_backoff(attempt, max=4s)
    await asyncio.sleep(wait_time)
    retry()
```

#### 4. **Retry with Backoff**
- 3 attempts per request (configurable)
- Exponential backoff: 1s, 2s, 4s
- Only retries transient errors (429, 500-599)
- Permanent errors (401, 404) fail fast

```python
# In core/retry.py
@retry(attempts=3, initial_backoff=1.0, backoff_factor=2.0)
def call_provider_api(target):
    return requests.get(f"https://api.example.com/{target}")
```

#### 5. **Result Normalization**
- Each provider returns different formats
- Normalizers convert to unified schema
- Consistent JSON structure for downstream processing

```python
# Raw Shodan response
{"ip": "1.2.3.4", "ports": [80, 443], ...}

# After normalization (core/normalizers/shodan.py)
{
    "ip_address": "1.2.3.4",
    "open_ports": [80, 443],
    "services": ["http", "https"],
    ...
}
```

---

## 📝 Common Tasks

### Task 1: Run Tests

```bash
# All tests
pytest -v

# Specific test file
pytest tests/test_orchestrator.py -v

# Specific test
pytest tests/test_orchestrator.py::test_orchestrate_all_providers -v

# With coverage
pytest --cov=core --cov=modules --cov-report=html

# Fast mode (skip slow tests)
pytest -m "not slow"
```

**Expected**: 51/51 passing, 0 failures

### Task 2: Check Code Quality

```bash
# Linting
flake8 . --count  # Should show ~0 errors

# Format check
black --check .
isort --check-only .

# Type checking
mypy core/ modules/ cli/

# Auto-fix formatting
black .
isort .
```

**Expected**: All tests pass, <1% violations

### Task 3: Add a Test

```bash
# 1. Create test file or add to existing
vim tests/test_my_feature.py

# 2. Write test
def test_my_feature():
    from core.module import BaseModule
    mod = BaseModule()
    assert mod.name is not None

# 3. Run test
pytest tests/test_my_feature.py -v

# 4. Add to CI/CD (automatic)
git push  # GitHub Actions runs all tests
```

### Task 4: Debug an Issue

```bash
# Verbose logging
export DARKRECONX_LOG_LEVEL=DEBUG
darkreconx pipeline --targets example.com --verbose

# Inspect cache
darkreconx cache --stats

# Test provider connection
darkreconx test-providers

# Check rate limits
darkreconx rate-limit --show
```

### Task 5: Update Documentation

```bash
# Main README
vim README.md

# Onboarding (this file)
vim docs/ONBOARDING.md

# Architecture deep-dive
vim docs/ARCHITECTURE.md

# Provider setup guide
vim docs/PROVIDERS_GUIDE.md
```

---

## 🔌 Adding Providers

### Quick Start: Add a New Provider in 30 Minutes

#### Step 1: Create Provider Module

```bash
mkdir -p modules/example_provider
touch modules/example_provider/__init__.py
touch modules/example_provider/scanner.py
```

#### Step 2: Implement Scanner

```python
# modules/example_provider/scanner.py
import os
import requests
from core.module import BaseModule
from core.retry import retry

class ExampleProviderModule(BaseModule):
    name = "example_provider"
    
    def __init__(self):
        self.api_key = os.environ.get("EXAMPLE_PROVIDER_API_KEY")
        self.base_url = "https://api.example.com"
    
    @retry(attempts=3, initial_backoff=1.0)
    def _call_api(self, target: str) -> dict:
        """Call provider API and return raw response"""
        if not self.api_key:
            return {"error": "Missing API key"}
        
        response = requests.get(
            f"{self.base_url}/lookup",
            params={"target": target, "api_key": self.api_key},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    async def execute_async(self, target: str) -> dict:
        """Async wrapper (required by BaseModule)"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_api, target)
    
    def normalize(self, raw_data: dict) -> dict:
        """Convert to unified schema"""
        return {
            "raw_response": raw_data,
            "normalized": {
                "example_field": raw_data.get("example_key")
            }
        }
```

#### Step 3: Create Normalizer

```python
# core/normalizers/example_provider.py
def normalize_example_provider(raw_data: dict) -> dict:
    """Convert example_provider response to unified schema"""
    if "error" in raw_data:
        return {"error": raw_data["error"]}
    
    return {
        "field1": raw_data.get("field1"),
        "field2": raw_data.get("field2"),
        # ... map all fields
    }
```

#### Step 4: Register Provider

```python
# core/orchestrator.py
from modules.example_provider import ExampleProviderModule

PROVIDERS = {
    # existing providers...
    "example_provider": ExampleProviderModule(),
}
```

#### Step 5: Test It

```bash
# Test provider directly
darkreconx enrich example.com --providers example_provider

# Add unit test
vim tests/test_example_provider.py

# Run test
pytest tests/test_example_provider.py -v
```

### Full Provider Example: See `CONTRIBUTING_MODULES.md`

---

## 🧪 Testing & Quality

### Running Tests

```bash
# All tests
pytest tests/ -v

# Watch mode (re-run on file change)
pytest-watch tests/

# Coverage report
pytest --cov=core --cov=modules --cov-report=html
open htmlcov/index.html
```

### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from unittest.mock import patch, AsyncMock

def test_sync_feature():
    """Test synchronous functionality"""
    from core.module import BaseModule
    mod = BaseModule()
    result = mod.some_method()
    assert result is not None

@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality"""
    from core.orchestrator import orchestrate_providers
    results = await orchestrate_providers("example.com")
    assert len(results) > 0
    assert "virustotal" in results

def test_with_mock():
    """Test with mocked API"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        from modules.example import ExampleModule
        mod = ExampleModule()
        result = mod._call_api("example.com")
        assert result["status"] == "ok"
```

### Code Quality Checklist

Before committing:

```bash
# 1. Format code
black .
isort .

# 2. Lint
flake8 .

# 3. Type check
mypy core/ modules/ cli/

# 4. Test
pytest tests/ -v

# 5. Git commit
git add .
git commit -m "Feature: Add X, fix Y"
```

---

## 🆘 Troubleshooting

### Issue: "API key not found"

**Problem**: Provider returns "Missing API key"

**Solution**:
```bash
# Check .env file
cat .env | grep YOUR_PROVIDER_KEY

# Or export directly
export YOUR_PROVIDER_API_KEY="your_actual_key"

# Test
darkreconx test-providers
```

### Issue: Tests Failing

**Problem**: `pytest` shows failures

**Solution**:
```bash
# Check test output
pytest tests/ -v -s

# Run specific failing test
pytest tests/test_X.py::test_Y -v -s

# Check dependencies
pip install -e ".[dev]"

# Clear cache
rm -rf .pytest_cache
pytest tests/ -v
```

### Issue: "Rate limit exceeded" (429)

**Problem**: Too many API requests

**Solution**:
```bash
# Reduce workers
darkreconx pipeline --targets example.com --max-workers 10

# Skip expensive providers
darkreconx pipeline --targets example.com --providers dns,virustotal

# Check rate limits
darkreconx rate-limit --show
```

### Issue: Slow Performance

**Problem**: Scans taking too long

**Solution**:
```bash
# Use cache (default, 70-90% hit rate)
# Already enabled, no action needed

# Skip unnecessary providers
darkreconx pipeline --targets example.com --providers dns

# Reduce timeout
export DARKRECONX_TIMEOUT=15
```

### Issue: Cache Not Working

**Problem**: Results not cached

**Solution**:
```bash
# Check cache
darkreconx cache --stats

# Clear old cache
darkreconx cache --clear

# Force refresh
darkreconx pipeline --targets example.com --refresh-cache

# Verify TTL
echo $DARKRECONX_CACHE_TTL  # Should be 86400
```

---

## 📚 Quick Reference

### Common Commands

```bash
# Installation
pip install -e ".[dev]"
pip install -r requirements.txt

# Running
darkreconx pipeline --targets example.com
darkreconx enrich 8.8.8.8 --type ip
darkreconx test-providers

# Testing
pytest tests/ -v
pytest --cov=core --cov=modules

# Code quality
black . && isort . && flake8 .

# Git
git clone https://github.com/GeoAziz/DarkReconX.git
git branch -b feature/my-feature
git push origin feature/my-feature
```

### Environment Variables

```bash
# API Keys
VT_API_KEY=your_key
SHODAN_API_KEY=your_key
DNSDB_API_KEY=your_key

# Performance
DARKRECONX_MAX_WORKERS=50
DARKRECONX_TIMEOUT=30
DARKRECONX_RETRY_ATTEMPTS=3

# Cache
DARKRECONX_CACHE_TTL=86400
DARKRECONX_NO_CACHE=0
DARKRECONX_REFRESH_CACHE=0

# Tor
TOR_ENABLED=false
TOR_SOCKS_PORT=9050
```

### File Locations

```
~/.darkreconx_cache/        # Cache directory
results/pipeline/           # Pipeline output
logs/darkreconx.log         # Log file (if enabled)
.env                        # Configuration (git-ignored)
```

---

## 🎯 Next Steps

1. **Get familiar**: Run a few scans, explore the code
2. **Join the team**: Introduce yourself in #darkreconx Slack
3. **Pick a task**: See CONTRIBUTING.md for open issues
4. **Submit PR**: Follow code quality checklist
5. **Get review**: Team will provide feedback
6. **Merge**: Congrats, you're a contributor!

---

## 📞 Need Help?

- **Questions**: Ask in #darkreconx Slack or GitHub issues
- **Bugs**: Create GitHub issue with reproduction steps
- **PRs**: See CONTRIBUTING.md for guidelines
- **Docs**: Check README.md and docs/ directory

---

## 🚀 Ready to Go!

You're all set! Start with:

```bash
# 1. Run first scan
darkreconx pipeline --targets example.com

# 2. Explore results
cat results/pipeline/summary.json

# 3. Read architecture
cat docs/ARCHITECTURE.md

# 4. Add a test
vim tests/test_my_feature.py

# 5. Create your first PR!
```

**Welcome to the team!** 🎉

