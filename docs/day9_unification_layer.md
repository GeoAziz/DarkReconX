# Day 9 - Multi-Provider Unification & Normalization Layer

**Date:** December 3, 2025  
**Status:** ✅ COMPLETED

## Overview

Day 9 introduces the **Multi-Provider Unification and Normalization Layer**, the most critical infrastructure component of DarkReconX to date. This layer solves the fundamental problem of inconsistent data structures across different enrichment providers.

## The Problem

Before Day 9, every provider returned wildly different data structures:

- **IPInfo** → `{city, region, ASN, org}`
- **WhoisXML** → `{WhoisRecord: {registrar, registrant, contacts}}`
- **VirusTotal** → `{data: {attributes: {...}}}`
- **DNS resolvers** → Tuples, lists, raw dnspython objects
- **Passive DNS** → Messy arrays

This inconsistency made the framework fragile and forced every upstream module to handle these differences manually.

## The Solution

Day 9 introduces a **single unified schema** that ALL providers must output. The system now:

1. **Normalizes** provider-specific responses into a common format
2. **Merges** data from multiple providers intelligently
3. **Deduplicates** arrays (IPs, MX, NS, TXT)
4. **Prioritizes** timestamps (earliest created, latest updated)
5. **Combines** risk scores and categories
6. **Preserves** all raw provider responses

## Architecture

### Unified Schema

All data flows through the `UnifiedRecord` dataclass:

```python
@dataclass
class UnifiedRecord:
    source: str           # Provider name
    type: str            # "domain", "ip", "url"
    target: str          # The target being enriched
    
    resolved: {
        "ip": [],        # A/AAAA records
        "mx": [],        # MX records
        "ns": [],        # Name servers
        "txt": [],       # TXT records
    }
    
    whois: {
        "registrar": None,
        "org": None,
        "country": None,
        "emails": [],
        "created": None,
        "updated": None,
        "expires": None,
    }
    
    network: {
        "asn": None,
        "asn_name": None,
        "isp": None,
        "city": None,
        "region": None,
        "country": None,
    }
    
    risk: {
        "score": None,      # 0-100
        "categories": [],   # Threat categories
        "malicious": False, # Boolean flag
    }
    
    raw: {}  # Original provider response
```

### Provider Normalizers

Each provider has its own normalizer in `core/normalizers/`:

#### IPInfo Normalizer
```python
from core.normalizers import normalize_ipinfo

response = {
    "ip": "8.8.8.8",
    "city": "Mountain View",
    "asn": {"asn": "AS15169", "name": "Google LLC"}
}

record = normalize_ipinfo(response, "8.8.8.8")
# Returns UnifiedRecord with network data populated
```

#### VirusTotal Normalizer
```python
from core.normalizers import normalize_virustotal

response = {
    "data": {
        "attributes": {
            "last_analysis_stats": {"malicious": 2, "clean": 88},
            "categories": {"Forcepoint": "phishing"}
        }
    }
}

record = normalize_virustotal(response, "malicious.com")
# Returns UnifiedRecord with risk data populated
```

#### WhoisXML Normalizer
```python
from core.normalizers import normalize_whoisxml

response = {
    "WhoisRecord": {
        "registrarName": "Example Registrar",
        "registrant": {"organization": "Example Corp"},
        "registryData": {
            "createdDate": "1995-08-14T04:00:00Z"
        }
    }
}

record = normalize_whoisxml(response, "example.com")
# Returns UnifiedRecord with WHOIS data populated
```

#### DNS Normalizer
```python
from core.normalizers import normalize_dns

response = {
    "A": ["93.184.216.34"],
    "MX": ["10 mail.example.com"],
    "NS": ["ns1.example.com", "ns2.example.com"]
}

record = normalize_dns(response, "example.com")
# Returns UnifiedRecord with DNS resolution data
```

### Merge Engine

The merge engine (`core/unify.py`) intelligently combines multiple UnifiedRecords:

```python
from core.unify import merge_records

# Collect records from multiple providers
ipinfo_record = normalize_ipinfo(ipinfo_response, "8.8.8.8")
virustotal_record = normalize_virustotal(vt_response, "8.8.8.8")
dns_record = normalize_dns(dns_response, "google.com")

# Merge into single comprehensive record
merged = merge_records([ipinfo_record, virustotal_record, dns_record])

# Result: UnifiedRecord with:
# - Deduplicated IPs, MX, NS, TXT
# - Earliest created date
# - Latest updated date
# - Maximum risk score
# - All categories combined
# - All raw responses preserved
```

### High-Level Unification API

For convenience, use the high-level unification function:

```python
from core.unify import unify_provider_data

providers_data = {
    "ipinfo": {...},      # Raw IPInfo response
    "virustotal": {...},  # Raw VirusTotal response
    "dns": {...}          # Raw DNS response
}

unified = unify_provider_data(
    target="8.8.8.8",
    target_type="ip",
    providers_data=providers_data
)

# Returns merged UnifiedRecord
```

## CLI Integration

### New `enrich` Command

```bash
# Pretty formatted output (default)
python cli/main.py enrich example.com --pretty

# JSON output
python cli/main.py enrich example.com --format json

# Minimal output
python cli/main.py enrich 8.8.8.8 --type ip --format min

# Specify providers
python cli/main.py enrich example.com --providers dns,whois,virustotal

# Save results
python cli/main.py enrich example.com --save results.json
```

### Output Formats

#### Pretty Format (--pretty)
Rich-formatted output with tables and panels:
- Target information panel
- DNS Resolution table
- WHOIS Information table
- Network Information table
- Risk Assessment panel

#### JSON Format (--json)
Raw JSON output for programmatic consumption:
```json
{
  "source": "merged",
  "type": "domain",
  "target": "example.com",
  "resolved": {...},
  "whois": {...},
  "network": {...},
  "risk": {...},
  "raw": {...}
}
```

#### Minimal Format (--min)
Compact single-line output:
```
Target: example.com
Type: domain
IPs: 93.184.216.34, 93.184.216.35
Location: Mountain View, US
```

## Merge Strategy

### Deduplication
Arrays are deduplicated while preserving order:
```python
# Provider 1: IPs = ["1.1.1.1", "2.2.2.2"]
# Provider 2: IPs = ["2.2.2.2", "3.3.3.3"]
# Merged:     IPs = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
```

### Timestamp Priority
- **Created dates**: Use earliest (original registration)
- **Updated dates**: Use latest (most recent change)
- **Expires dates**: Use latest (furthest expiration)

### Risk Scoring
- **Risk score**: Use maximum across all providers (conservative)
- **Malicious flag**: Set to True if ANY provider reports malicious
- **Categories**: Combine and deduplicate all categories

### Field Selection
For single-value fields (city, country, ASN):
- Use first non-empty value encountered
- Later providers can fill in missing fields
- Earlier providers take precedence for fields they provide

## Testing

Comprehensive test suite in `tests/test_unification_layer.py`:

### Test Coverage
- ✅ UnifiedRecord schema validation
- ✅ IPInfo normalization (full, partial, empty)
- ✅ VirusTotal normalization (malicious, clean, DNS records)
- ✅ WhoisXML normalization (full, malformed, missing fields)
- ✅ DNS normalization (dict, list, tuples, empty)
- ✅ Merge deduplication
- ✅ Timestamp prioritization
- ✅ Risk score maximization
- ✅ Category merging
- ✅ Provider outage handling
- ✅ Unicode handling
- ✅ IPv6 addresses
- ✅ Null value handling
- ✅ Very long TXT records

### Running Tests
```bash
# Run all unification tests
pytest tests/test_unification_layer.py -v

# Run specific test class
pytest tests/test_unification_layer.py::TestMergeEngine -v

# Run with coverage
pytest tests/test_unification_layer.py --cov=core.normalizers --cov=core.unify
```

## File Structure

```
core/
├── unified_record.py         # UnifiedRecord schema definition
├── unify.py                   # Merge engine
└── normalizers/
    ├── __init__.py           # Normalizer exports
    ├── ipinfo.py             # IPInfo normalizer
    ├── virustotal.py         # VirusTotal normalizer
    ├── whoisxml.py           # WhoisXML normalizer
    └── dns.py                # DNS normalizer

tests/
└── test_unification_layer.py # Comprehensive test suite

cli/
└── main.py                   # Enhanced with enrich command
```

## Integration Examples

### In a Module

```python
from core.normalizers import normalize_dns
from core.unified_record import UnifiedRecord

class MyModule:
    def scan(self, target):
        # Get DNS data
        dns_data = self.query_dns(target)
        
        # Normalize to UnifiedRecord
        record = normalize_dns(dns_data, target)
        
        # Now work with consistent structure
        for ip in record.resolved["ip"]:
            self.analyze_ip(ip)
```

### Combining Multiple Providers

```python
from core.unify import unify_provider_data

def enrich_target(target):
    # Gather data from all available providers
    providers = {}
    
    if ipinfo_available:
        providers["ipinfo"] = query_ipinfo(target)
    
    if virustotal_available:
        providers["virustotal"] = query_virustotal(target)
    
    if whois_available:
        providers["whoisxml"] = query_whoisxml(target)
    
    # Unify and return
    return unify_provider_data(target, "domain", providers)
```

## Benefits

### For Module Developers
- **Consistent interface**: Work with same structure regardless of provider
- **Less code**: No need to handle provider-specific quirks
- **Type safety**: Strong typing with dataclasses
- **Easy testing**: Mock UnifiedRecords instead of raw API responses

### For Framework
- **Reliability**: Centralized normalization reduces bugs
- **Maintainability**: Provider changes only affect one normalizer
- **Extensibility**: New providers just need a normalizer
- **Composability**: Easy to combine data from multiple sources

### For Users
- **Richer data**: Automatic merging gives comprehensive results
- **Flexibility**: Choose output format (pretty, JSON, minimal)
- **Transparency**: Raw provider data always preserved
- **Consistency**: Same structure whether using one provider or many

## Future Enhancements

Potential additions for Day 10+:

1. **Passive DNS normalizer** - Support CIRCL, SecurityTrails passive DNS
2. **Shodan normalizer** - Integrate Shodan search results
3. **AlienVault OTX normalizer** - Threat intelligence data
4. **Censys normalizer** - Internet-wide scan data
5. **Confidence scores** - Track data source reliability
6. **Conflict resolution** - Handle contradictory data
7. **Caching layer** - Cache normalized records
8. **Streaming API** - Real-time provider updates

## Conclusion

Day 9 establishes the foundation for all future enrichment features. Every new provider, every new data source, will output the same unified format. This makes DarkReconX:

- **Predictable** - Same structure everywhere
- **Composable** - Mix and match providers freely
- **Maintainable** - Changes isolated to normalizers
- **Professional** - Enterprise-grade data handling

The unification layer is now the single source of truth for all provider data in DarkReconX.

---

**Day 9 Complete ✅**

All deliverables implemented:
- ✅ `unified_record.py` with exact schema
- ✅ All four normalizers (IPInfo, VirusTotal, WhoisXML, DNS)
- ✅ Full merge engine with deduplication
- ✅ Comprehensive test suite
- ✅ CLI upgrade with `--json`, `--pretty`, `--min`
- ✅ Complete documentation

**Next:** Day 10 will build on this foundation with advanced features.
