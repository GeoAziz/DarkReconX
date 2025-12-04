#!/usr/bin/env python3
"""
Day 9 Demonstration - Unification Layer

This script demonstrates the multi-provider unification layer in action.
It shows how different provider responses are normalized and merged into
a single, consistent UnifiedRecord.

Run: python examples/day9_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json

from rich import box
from rich.console import Console
from rich.panel import Panel

from core.normalizers import normalize_dns, normalize_ipinfo, normalize_virustotal, normalize_whoisxml
from core.unified_record import UnifiedRecord, create_empty_record
from core.unify import merge_records

console = Console()


def demo_ipinfo_normalization():
    """Demonstrate IPInfo response normalization"""
    console.print("\n[bold cyan]1. IPInfo Normalization[/bold cyan]")
    console.print("=" * 60)

    # Simulate IPInfo response
    ipinfo_response = {
        "ip": "8.8.8.8",
        "hostname": "dns.google",
        "city": "Mountain View",
        "region": "California",
        "country": "US",
        "org": "AS15169 Google LLC",
        "asn": {"asn": "AS15169", "name": "Google LLC", "domain": "google.com"},
    }

    console.print("\n[yellow]Raw IPInfo Response:[/yellow]")
    console.print(json.dumps(ipinfo_response, indent=2))

    # Normalize
    record = normalize_ipinfo(ipinfo_response, "8.8.8.8")

    console.print("\n[green]✓ Normalized to UnifiedRecord[/green]")
    console.print(f"Source: {record.source}")
    console.print(f"Type: {record.type}")
    console.print(f"Network ASN: {record.network['asn']}")
    console.print(f"Network City: {record.network['city']}")
    console.print(f"Network Country: {record.network['country']}")


def demo_virustotal_normalization():
    """Demonstrate VirusTotal response normalization"""
    console.print("\n\n[bold cyan]2. VirusTotal Normalization[/bold cyan]")
    console.print("=" * 60)

    # Simulate VirusTotal response
    vt_response = {
        "data": {
            "id": "malicious.example.com",
            "attributes": {
                "last_analysis_stats": {"malicious": 15, "suspicious": 3, "clean": 70},
                "categories": {"Forcepoint": "phishing", "BitDefender": "malware", "Sophos": "phishing"},
                "reputation": -42,
                "last_dns_records": [
                    {"type": "A", "value": "192.0.2.1"},
                    {"type": "MX", "value": "mail.malicious.example.com"},
                ],
            },
        }
    }

    console.print("\n[yellow]Raw VirusTotal Response:[/yellow]")
    console.print(json.dumps(vt_response, indent=2)[:500] + "...")

    # Normalize
    record = normalize_virustotal(vt_response, "malicious.example.com")

    console.print("\n[green]✓ Normalized to UnifiedRecord[/green]")
    console.print(f"Source: {record.source}")
    console.print(f"Risk Malicious: {record.risk['malicious']}")
    console.print(f"Risk Score: {record.risk['score']}")
    console.print(f"Risk Categories: {record.risk['categories']}")
    console.print(f"Resolved IPs: {record.resolved['ip']}")


def demo_whoisxml_normalization():
    """Demonstrate WhoisXML response normalization"""
    console.print("\n\n[bold cyan]3. WhoisXML Normalization[/bold cyan]")
    console.print("=" * 60)

    # Simulate WhoisXML response
    whoisxml_response = {
        "WhoisRecord": {
            "domainName": "example.com",
            "registrarName": "Example Registrar, Inc.",
            "registrant": {"organization": "Example Organization", "country": "US", "email": "admin@example.com"},
            "technicalContact": {"email": "tech@example.com"},
            "registryData": {
                "createdDate": "1995-08-14T04:00:00Z",
                "updatedDate": "2023-08-14T07:01:31Z",
                "expiresDate": "2024-08-13T04:00:00Z",
            },
            "nameServers": {"hostNames": ["ns1.example.com", "ns2.example.com"]},
        }
    }

    console.print("\n[yellow]Raw WhoisXML Response:[/yellow]")
    console.print(json.dumps(whoisxml_response, indent=2)[:500] + "...")

    # Normalize
    record = normalize_whoisxml(whoisxml_response, "example.com")

    console.print("\n[green]✓ Normalized to UnifiedRecord[/green]")
    console.print(f"Source: {record.source}")
    console.print(f"WHOIS Registrar: {record.whois['registrar']}")
    console.print(f"WHOIS Organization: {record.whois['org']}")
    console.print(f"WHOIS Created: {record.whois['created']}")
    console.print(f"WHOIS Emails: {record.whois['emails']}")
    console.print(f"Resolved NS: {record.resolved['ns']}")


def demo_dns_normalization():
    """Demonstrate DNS response normalization"""
    console.print("\n\n[bold cyan]4. DNS Normalization[/bold cyan]")
    console.print("=" * 60)

    # Simulate DNS response
    dns_response = {
        "A": ["93.184.216.34", "93.184.216.35"],
        "MX": ["10 mail.example.com", "20 mail2.example.com"],
        "NS": ["ns1.example.com", "ns2.example.com"],
        "TXT": ["v=spf1 include:_spf.example.com ~all"],
    }

    console.print("\n[yellow]Raw DNS Response:[/yellow]")
    console.print(json.dumps(dns_response, indent=2))

    # Normalize
    record = normalize_dns(dns_response, "example.com")

    console.print("\n[green]✓ Normalized to UnifiedRecord[/green]")
    console.print(f"Source: {record.source}")
    console.print(f"Resolved IPs: {record.resolved['ip']}")
    console.print(f"Resolved MX: {record.resolved['mx']}")
    console.print(f"Resolved NS: {record.resolved['ns']}")
    console.print(f"Resolved TXT: {record.resolved['txt']}")


def demo_merge_engine():
    """Demonstrate merging multiple provider records"""
    console.print("\n\n[bold cyan]5. Merge Engine - Combining Multiple Providers[/bold cyan]")
    console.print("=" * 60)

    # Create records from different providers
    ipinfo_record = create_empty_record("ipinfo", "example.com", "domain")
    ipinfo_record.network["city"] = "Mountain View"
    ipinfo_record.network["country"] = "US"
    ipinfo_record.network["asn"] = "AS15169"

    vt_record = create_empty_record("virustotal", "example.com", "domain")
    vt_record.resolved["ip"] = ["93.184.216.34"]
    vt_record.risk["score"] = 5.2
    vt_record.risk["malicious"] = False
    vt_record.risk["categories"] = ["web_ads"]

    dns_record = create_empty_record("dns", "example.com", "domain")
    dns_record.resolved["ip"] = ["93.184.216.34", "93.184.216.35"]  # Has duplicate
    dns_record.resolved["mx"] = ["10 mail.example.com"]
    dns_record.resolved["ns"] = ["ns1.example.com", "ns2.example.com"]

    whois_record = create_empty_record("whoisxml", "example.com", "domain")
    whois_record.whois["registrar"] = "Example Registrar"
    whois_record.whois["org"] = "Example Corp"
    whois_record.whois["created"] = "1995-08-14T04:00:00Z"
    whois_record.whois["emails"] = ["admin@example.com"]

    console.print("\n[yellow]Merging 4 provider records:[/yellow]")
    console.print("  • IPInfo (network data)")
    console.print("  • VirusTotal (risk data, 1 IP)")
    console.print("  • DNS (2 IPs including duplicate, MX, NS)")
    console.print("  • WhoisXML (WHOIS data)")

    # Merge all records
    merged = merge_records([ipinfo_record, vt_record, dns_record, whois_record])

    console.print("\n[green]✓ Merged into single UnifiedRecord[/green]")

    # Display merged result
    result_content = f"""
[bold]Source:[/bold] {merged.source}
[bold]Target:[/bold] {merged.target}

[bold cyan]Resolved (Deduplicated):[/bold cyan]
  IPs: {', '.join(merged.resolved['ip'])}
  MX: {', '.join(merged.resolved['mx'])}
  NS: {', '.join(merged.resolved['ns'])}

[bold cyan]Network:[/bold cyan]
  ASN: {merged.network['asn']}
  City: {merged.network['city']}
  Country: {merged.network['country']}

[bold cyan]WHOIS:[/bold cyan]
  Registrar: {merged.whois['registrar']}
  Organization: {merged.whois['org']}
  Created: {merged.whois['created']}
  Emails: {', '.join(merged.whois['emails'])}

[bold cyan]Risk:[/bold cyan]
  Malicious: {merged.risk['malicious']}
  Score: {merged.risk['score']}
  Categories: {', '.join(merged.risk['categories'])}
"""

    console.print(Panel(result_content.strip(), title="[bold yellow]Merged Result[/bold yellow]", box=box.ROUNDED))

    console.print("\n[bold green]Key Features Demonstrated:[/bold green]")
    console.print("  ✓ Deduplication: 93.184.216.34 appeared in 2 providers, only listed once")
    console.print("  ✓ Combination: Data from all 4 providers combined")
    console.print("  ✓ No data loss: All fields preserved")
    console.print("  ✓ Consistent structure: Same format regardless of source")


def main():
    """Run all demonstrations"""
    console.print(
        Panel(
            "[bold yellow]Day 9 - Multi-Provider Unification Layer Demo[/bold yellow]\n\n"
            "This demo shows how different provider responses are normalized\n"
            "and merged into a single, consistent UnifiedRecord format.",
            box=box.DOUBLE,
        )
    )

    demo_ipinfo_normalization()
    demo_virustotal_normalization()
    demo_whoisxml_normalization()
    demo_dns_normalization()
    demo_merge_engine()

    console.print("\n\n" + "=" * 60)
    console.print("[bold green]✓ Day 9 Demonstration Complete![/bold green]")
    console.print("\nAll providers now output the same unified format.")
    console.print("This ensures consistency across the entire framework.")
    console.print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
