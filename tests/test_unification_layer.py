"""
Unit Tests for Day 9 - Unification Layer

Tests cover:
- UnifiedRecord schema validation
- Provider normalizers (IPInfo, VirusTotal, WhoisXML, DNS)
- Merge engine correctness
- Partial data handling
- Missing fields
- Malformed WHOIS
- DNS edge cases
- Provider API outage handling

Author: DarkReconX Contributors
Date: December 3, 2025 - Day 9
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from core.normalizers.dns import normalize_dns, normalize_dns_bulk
from core.normalizers.ipinfo import normalize_ipinfo
from core.normalizers.virustotal import normalize_virustotal
from core.normalizers.whoisxml import normalize_whoisxml
from core.unified_record import UnifiedRecord, create_empty_record, validate_record
from core.unify import _merge_network, _merge_resolved, _merge_risk, _merge_whois, merge_records, unify_provider_data


class TestUnifiedRecordSchema:
    """Test the UnifiedRecord schema and validation"""

    def test_create_empty_record(self):
        """Test creating an empty record with defaults"""
        record = create_empty_record("test", "example.com", "domain")

        assert record.source == "test"
        assert record.target == "example.com"
        assert record.type == "domain"
        assert record.resolved == {"ip": [], "mx": [], "ns": [], "txt": []}
        assert "registrar" in record.whois
        assert "asn" in record.network
        assert "score" in record.risk

    def test_validate_record_valid(self):
        """Test validation of a valid record"""
        record = create_empty_record("test", "example.com", "domain")
        assert validate_record(record) is True

    def test_validate_record_invalid_type(self):
        """Test validation fails with invalid type"""
        record = create_empty_record("test", "example.com", "invalid_type")
        assert validate_record(record) is False

    def test_record_to_dict(self):
        """Test converting record to dictionary"""
        record = create_empty_record("test", "example.com", "domain")
        record_dict = record.to_dict()

        assert isinstance(record_dict, dict)
        assert record_dict["source"] == "test"
        assert record_dict["target"] == "example.com"


class TestIPInfoNormalizer:
    """Test IPInfo.io response normalization"""

    def test_normalize_ipinfo_full_response(self):
        """Test normalizing a complete IPInfo response"""
        resp = {
            "ip": "8.8.8.8",
            "hostname": "dns.google",
            "city": "Mountain View",
            "region": "California",
            "country": "US",
            "org": "AS15169 Google LLC",
            "asn": {"asn": "AS15169", "name": "Google LLC", "domain": "google.com"},
        }

        record = normalize_ipinfo(resp, "8.8.8.8")

        assert record.source == "ipinfo"
        assert record.type == "ip"
        assert record.target == "8.8.8.8"
        assert record.network["asn"] == "AS15169"
        assert record.network["asn_name"] == "Google LLC"
        assert record.network["city"] == "Mountain View"
        assert record.network["region"] == "California"
        assert record.network["country"] == "US"
        assert record.network["isp"] == "AS15169 Google LLC"
        assert "dns.google" in record.resolved["ip"]

    def test_normalize_ipinfo_partial_data(self):
        """Test normalizing IPInfo response with missing fields"""
        resp = {"ip": "1.1.1.1", "country": "AU"}

        record = normalize_ipinfo(resp, "1.1.1.1")

        assert record.source == "ipinfo"
        assert record.network["country"] == "AU"
        assert record.network["city"] is None
        assert record.network["asn"] is None

    def test_normalize_ipinfo_empty_response(self):
        """Test normalizing empty IPInfo response"""
        resp = {}

        record = normalize_ipinfo(resp, "0.0.0.0")

        assert record.source == "ipinfo"
        assert record.target == "0.0.0.0"
        assert all(v is None for k, v in record.network.items())


class TestVirusTotalNormalizer:
    """Test VirusTotal response normalization"""

    def test_normalize_virustotal_malicious(self):
        """Test normalizing VirusTotal response with malicious detection"""
        resp = {
            "data": {
                "id": "malicious.com",
                "attributes": {
                    "last_analysis_stats": {"malicious": 10, "suspicious": 5, "clean": 85},
                    "categories": {"Forcepoint": "phishing", "BitDefender": "malware"},
                    "reputation": -50,
                },
            }
        }

        record = normalize_virustotal(resp, "malicious.com")

        assert record.source == "virustotal"
        assert record.type == "domain"
        assert record.risk["malicious"] is True
        assert record.risk["score"] > 0
        assert "phishing" in record.risk["categories"]
        assert "malware" in record.risk["categories"]

    def test_normalize_virustotal_clean(self):
        """Test normalizing VirusTotal response with clean result"""
        resp = {
            "data": {
                "id": "google.com",
                "attributes": {"last_analysis_stats": {"malicious": 0, "suspicious": 0, "clean": 90}, "reputation": 1500},
            }
        }

        record = normalize_virustotal(resp, "google.com")

        assert record.risk["malicious"] is False
        assert record.risk["score"] == 0.0

    def test_normalize_virustotal_with_dns(self):
        """Test normalizing VirusTotal response with DNS records"""
        resp = {
            "data": {
                "id": "example.com",
                "attributes": {
                    "last_analysis_stats": {"malicious": 0, "clean": 80},
                    "last_dns_records": [
                        {"type": "A", "value": "93.184.216.34"},
                        {"type": "MX", "value": "mail.example.com"},
                        {"type": "NS", "value": "ns1.example.com"},
                    ],
                },
            }
        }

        record = normalize_virustotal(resp, "example.com")

        assert "93.184.216.34" in record.resolved["ip"]
        assert "mail.example.com" in record.resolved["mx"]
        assert "ns1.example.com" in record.resolved["ns"]

    def test_normalize_virustotal_ip(self):
        """Test normalizing VirusTotal IP response"""
        resp = {
            "data": {
                "id": "8.8.8.8",
                "attributes": {
                    "asn": 15169,
                    "as_owner": "Google LLC",
                    "country": "US",
                    "last_analysis_stats": {"malicious": 0, "clean": 89},
                },
            }
        }

        record = normalize_virustotal(resp, "8.8.8.8")

        assert record.type == "ip"
        assert record.network["asn"] == "AS15169"
        assert record.network["asn_name"] == "Google LLC"
        assert record.network["country"] == "US"


class TestWhoisXMLNormalizer:
    """Test WhoisXML response normalization"""

    def test_normalize_whoisxml_full_response(self):
        """Test normalizing complete WhoisXML response"""
        resp = {
            "WhoisRecord": {
                "domainName": "example.com",
                "registrarName": "Example Registrar, Inc.",
                "registrant": {"organization": "Example Corp", "country": "US", "email": "admin@example.com"},
                "administrativeContact": {"email": "admin@example.com"},
                "technicalContact": {"email": "tech@example.com"},
                "registryData": {
                    "createdDate": "1995-08-14T04:00:00Z",
                    "updatedDate": "2023-08-14T07:01:31Z",
                    "expiresDate": "2024-08-13T04:00:00Z",
                },
                "nameServers": {"hostNames": ["ns1.example.com", "ns2.example.com"]},
            }
        }

        record = normalize_whoisxml(resp, "example.com")

        assert record.source == "whoisxml"
        assert record.type == "domain"
        assert record.whois["registrar"] == "Example Registrar, Inc."
        assert record.whois["org"] == "Example Corp"
        assert record.whois["country"] == "US"
        assert "admin@example.com" in record.whois["emails"]
        assert "tech@example.com" in record.whois["emails"]
        assert record.whois["created"] == "1995-08-14T04:00:00Z"
        assert "ns1.example.com" in record.resolved["ns"]
        assert "ns2.example.com" in record.resolved["ns"]

    def test_normalize_whoisxml_malformed(self):
        """Test normalizing malformed WhoisXML response"""
        resp = {"WhoisRecord": {"domainName": "test.com", "registrant": "InvalidFormat"}}  # Should be dict

        record = normalize_whoisxml(resp, "test.com")

        assert record.source == "whoisxml"
        assert record.whois["org"] is None

    def test_normalize_whoisxml_missing_fields(self):
        """Test normalizing WhoisXML response with missing fields"""
        resp = {"WhoisRecord": {"domainName": "minimal.com"}}

        record = normalize_whoisxml(resp, "minimal.com")

        assert record.source == "whoisxml"
        assert record.whois["registrar"] is None
        assert len(record.whois["emails"]) == 0


class TestDNSNormalizer:
    """Test DNS resolver response normalization"""

    def test_normalize_dns_dict_format(self):
        """Test normalizing DNS response in dictionary format"""
        resp = {
            "A": ["93.184.216.34", "93.184.216.35"],
            "MX": ["10 mail.example.com"],
            "NS": ["ns1.example.com", "ns2.example.com"],
            "TXT": ["v=spf1 include:_spf.example.com ~all"],
        }

        record = normalize_dns(resp, "example.com")

        assert record.source == "dns"
        assert record.type == "domain"
        assert "93.184.216.34" in record.resolved["ip"]
        assert "93.184.216.35" in record.resolved["ip"]
        assert "10 mail.example.com" in record.resolved["mx"]
        assert "ns1.example.com" in record.resolved["ns"]
        assert len(record.resolved["txt"]) == 1

    def test_normalize_dns_list_format(self):
        """Test normalizing DNS response in list format"""
        resp = ["93.184.216.34", "93.184.216.35"]

        record = normalize_dns(resp, "example.com", record_type="A")

        assert "93.184.216.34" in record.resolved["ip"]
        assert "93.184.216.35" in record.resolved["ip"]

    def test_normalize_dns_empty(self):
        """Test normalizing empty DNS response"""
        resp = {}

        record = normalize_dns(resp, "example.com")

        assert record.source == "dns"
        assert len(record.resolved["ip"]) == 0

    def test_normalize_dns_mx_tuples(self):
        """Test normalizing MX records as tuples"""
        resp = {"MX": [(10, "mail1.example.com"), (20, "mail2.example.com")]}

        record = normalize_dns(resp, "example.com")

        assert "10 mail1.example.com" in record.resolved["mx"]
        assert "20 mail2.example.com" in record.resolved["mx"]


class TestMergeEngine:
    """Test the merge engine"""

    def test_merge_single_record(self):
        """Test merging a single record returns itself"""
        record = create_empty_record("test", "example.com", "domain")
        merged = merge_records([record])

        assert merged.source == "test"

    def test_merge_resolved_deduplication(self):
        """Test that resolved records are deduplicated"""
        record1 = create_empty_record("dns1", "example.com", "domain")
        record1.resolved["ip"] = ["1.1.1.1", "2.2.2.2"]

        record2 = create_empty_record("dns2", "example.com", "domain")
        record2.resolved["ip"] = ["2.2.2.2", "3.3.3.3"]  # Duplicate 2.2.2.2

        merged = _merge_resolved([record1, record2])

        assert len(merged["ip"]) == 3
        assert "1.1.1.1" in merged["ip"]
        assert "2.2.2.2" in merged["ip"]
        assert "3.3.3.3" in merged["ip"]

    def test_merge_whois_dates(self):
        """Test that WHOIS dates are properly merged"""
        record1 = create_empty_record("whois1", "example.com", "domain")
        record1.whois["created"] = "2000-01-01T00:00:00Z"
        record1.whois["updated"] = "2020-01-01T00:00:00Z"

        record2 = create_empty_record("whois2", "example.com", "domain")
        record2.whois["created"] = "2005-01-01T00:00:00Z"  # Later
        record2.whois["updated"] = "2023-01-01T00:00:00Z"  # More recent

        merged = _merge_whois([record1, record2])

        # Should use earliest created date
        assert merged["created"] == "2000-01-01T00:00:00Z"
        # Should use latest updated date
        assert merged["updated"] == "2023-01-01T00:00:00Z"

    def test_merge_network_first_non_empty(self):
        """Test that network data uses first non-empty value"""
        record1 = create_empty_record("provider1", "8.8.8.8", "ip")
        record1.network["city"] = "Mountain View"
        record1.network["asn"] = None

        record2 = create_empty_record("provider2", "8.8.8.8", "ip")
        record2.network["city"] = "Different City"  # Should be ignored
        record2.network["asn"] = "AS15169"  # Should be used (first was None)

        merged = _merge_network([record1, record2])

        assert merged["city"] == "Mountain View"
        assert merged["asn"] == "AS15169"

    def test_merge_risk_maximum_score(self):
        """Test that risk score uses maximum value"""
        record1 = create_empty_record("vt1", "bad.com", "domain")
        record1.risk["score"] = 15.5
        record1.risk["malicious"] = False

        record2 = create_empty_record("vt2", "bad.com", "domain")
        record2.risk["score"] = 85.2  # Higher score
        record2.risk["malicious"] = True

        merged = _merge_risk([record1, record2])

        assert merged["score"] == 85.2
        assert merged["malicious"] is True  # ANY malicious flag sets to True

    def test_merge_risk_categories(self):
        """Test that risk categories are merged and deduplicated"""
        record1 = create_empty_record("vt1", "bad.com", "domain")
        record1.risk["categories"] = ["phishing", "malware"]

        record2 = create_empty_record("vt2", "bad.com", "domain")
        record2.risk["categories"] = ["malware", "spam"]  # Duplicate "malware"

        merged = _merge_risk([record1, record2])

        assert len(merged["categories"]) == 3
        assert "phishing" in merged["categories"]
        assert "malware" in merged["categories"]
        assert "spam" in merged["categories"]

    def test_merge_full_records(self):
        """Test merging complete records from multiple providers"""
        # IPInfo record
        ipinfo_record = create_empty_record("ipinfo", "8.8.8.8", "ip")
        ipinfo_record.network["city"] = "Mountain View"
        ipinfo_record.network["asn"] = "AS15169"

        # VirusTotal record
        vt_record = create_empty_record("virustotal", "8.8.8.8", "ip")
        vt_record.risk["score"] = 0.0
        vt_record.risk["malicious"] = False
        vt_record.network["country"] = "US"

        merged = merge_records([ipinfo_record, vt_record])

        assert merged.source == "merged"
        assert merged.target == "8.8.8.8"
        assert merged.network["city"] == "Mountain View"
        assert merged.network["asn"] == "AS15169"
        assert merged.network["country"] == "US"
        assert merged.risk["malicious"] is False

    def test_merge_empty_list(self):
        """Test merging empty list of records"""
        merged = merge_records([])

        assert merged.source == "merged"
        assert merged.target == ""


class TestProviderOutageHandling:
    """Test handling of provider API outages and errors"""

    def test_unify_with_failed_provider(self):
        """Test that unification continues when one provider fails"""
        providers_data = {
            "ipinfo": {"ip": "8.8.8.8", "city": "Mountain View"},
            "virustotal": None,  # Simulating API failure
            "dns": {"A": ["8.8.8.8"]},
        }

        # Should not crash, should process available providers
        with patch("core.normalizers.virustotal.normalize_virustotal", side_effect=Exception("API Error")):
            try:
                result = unify_provider_data("8.8.8.8", "ip", providers_data)
                # Should still have data from ipinfo and dns
                assert result.source == "merged"
            except Exception:
                pytest.fail("Unification should not fail when one provider errors")


class TestEdgeCases:
    """Test edge cases and unusual scenarios"""

    def test_unicode_in_whois(self):
        """Test handling of Unicode characters in WHOIS data"""
        resp = {"WhoisRecord": {"domainName": "tëst.com", "registrant": {"organization": "Tëst Ørg", "country": "NÖ"}}}

        record = normalize_whoisxml(resp, "tëst.com")

        assert record.whois["org"] == "Tëst Ørg"

    def test_very_long_txt_records(self):
        """Test handling of very long TXT records"""
        long_txt = "v=DKIM1; k=rsa; p=" + "A" * 1000
        resp = {"TXT": [long_txt]}

        record = normalize_dns(resp, "example.com")

        assert long_txt in record.resolved["txt"]

    def test_ipv6_addresses(self):
        """Test handling of IPv6 addresses"""
        resp = {"AAAA": ["2001:4860:4860::8888", "2001:4860:4860::8844"]}

        record = normalize_dns(resp, "google.com")

        assert "2001:4860:4860::8888" in record.resolved["ip"]

    def test_null_values_in_response(self):
        """Test handling of null values in provider responses"""
        resp = {"ip": "1.1.1.1", "city": None, "region": None, "country": "AU"}

        record = normalize_ipinfo(resp, "1.1.1.1")

        assert record.network["country"] == "AU"
        assert record.network["city"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
