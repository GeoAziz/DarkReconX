"""tests/test_result_merger.py

Tests for unified result merging and deduplication.
"""

import pytest

from core.result_merger import ResultDeduplicator, ResultMerger, merge_results


class TestResultMerger:
    """Test result merging."""

    def test_merge_single_provider(self):
        """Test merging single provider result."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ip": "1.2.3.4", "domain": "example.com"},
            }
        }

        merged = ResultMerger.merge("example.com", results)

        assert merged["target"] == "example.com"
        assert merged["summary"]["total_providers"] == 1
        assert merged["summary"]["successful_providers"] == 1
        # Data is merged by field, not by provider
        assert "ip" in merged["data"]
        assert "domain" in merged["data"]

    def test_merge_multiple_providers(self):
        """Test merging multiple provider results."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ip": "1.2.3.4"},
                "execution_time_seconds": 0.5,
            },
            "provider2": {
                "success": True,
                "data": {"ip": "5.6.7.8"},
                "execution_time_seconds": 0.3,
            },
        }

        merged = ResultMerger.merge("example.com", results)

        assert merged["summary"]["successful_providers"] == 2
        # Data is merged by field (both providers report 'ip')
        assert "ip" in merged["data"]
        assert "values" in merged["data"]["ip"]
        assert len(merged["data"]["ip"]["values"]) == 2

    def test_merge_with_errors(self):
        """Test merging with provider errors."""
        results = {
            "provider1": {"success": True, "data": {"ip": "1.2.3.4"}},
            "provider2": {"success": False, "error": "Rate limit exceeded"},
        }

        merged = ResultMerger.merge("example.com", results)

        assert merged["summary"]["successful_providers"] == 1
        assert merged["summary"]["failed_providers"] == 1
        assert "provider2" in merged["errors"]
        assert not merged["summary"]["success"]

    def test_merge_field_deduplication(self):
        """Test field-level deduplication."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ips": ["1.2.3.4", "5.6.7.8"]},
            },
            "provider2": {
                "success": True,
                "data": {"ips": ["5.6.7.8", "9.10.11.12"]},
            },
        }

        merged = ResultMerger.merge("example.com", results)

        assert "ips" in merged["data"]
        assert "values" in merged["data"]["ips"]
        # Both providers tracked as sources
        assert "provider1" in merged["data"]["ips"]["sources"]
        assert "provider2" in merged["data"]["ips"]["sources"]

    def test_merge_with_raw_data(self):
        """Test including raw provider responses."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ip": "1.2.3.4"},
                "raw": {"full_response": "..."},
            }
        }

        merged = ResultMerger.merge("example.com", results, include_raw=True)

        assert "provider1" in merged["providers"]
        assert merged["providers"]["provider1"]["raw"] == {"full_response": "..."}


class TestResultDeduplicator:
    """Test result deduplication."""

    def test_deduplicate_ips(self):
        """Test IP deduplication."""
        ips = ["1.2.3.4", "5.6.7.8", "1.2.3.4", "9.10.11.12"]
        dedup = ResultDeduplicator.deduplicate_ips(ips)

        assert len(dedup) == 3
        assert dedup == ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

    def test_deduplicate_domains(self):
        """Test domain deduplication (case-insensitive)."""
        domains = ["example.com", "test.org", "EXAMPLE.COM", "test.org"]
        dedup = ResultDeduplicator.deduplicate_domains(domains)

        assert len(dedup) == 2
        # Original case preserved for first occurrence
        assert dedup[0].lower() == "example.com"
        assert dedup[1].lower() == "test.org"

    def test_deduplicate_dns_records(self):
        """Test DNS record deduplication."""
        records = [
            {"type": "A", "value": "1.2.3.4"},
            {"type": "A", "value": "5.6.7.8"},
            {"type": "A", "value": "1.2.3.4"},  # Duplicate
            {"type": "CNAME", "value": "alias.example.com"},
        ]

        dedup = ResultDeduplicator.deduplicate_dns_records(records)

        assert len(dedup) == 3
        assert dedup[0] == {"type": "A", "value": "1.2.3.4"}
        assert dedup[2] == {"type": "CNAME", "value": "alias.example.com"}

    def test_deduplicate_dns_case_insensitive(self):
        """Test DNS record deduplication is case-insensitive."""
        records = [
            {"type": "A", "value": "EXAMPLE.COM"},
            {"type": "A", "value": "example.com"},
        ]

        dedup = ResultDeduplicator.deduplicate_dns_records(records)

        # Should be treated as same (case-insensitive on value)
        assert len(dedup) == 1

    def test_merge_metadata(self):
        """Test metadata merging."""
        metadata_list = [
            {"key1": "value1", "key2": "value2"},
            {"key2": "value2_override", "key3": "value3"},
        ]

        merged = ResultDeduplicator.merge_metadata(metadata_list)

        # Merge prefers non-None values
        assert merged["key1"] == "value1"
        assert merged["key2"] == "value2_override"  # Last non-None value wins
        assert merged["key3"] == "value3"


class TestMergeResultsFunction:
    """Test merge_results convenience function."""

    def test_merge_with_deduplication(self):
        """Test merge_results with deduplication."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ips": ["1.2.3.4", "1.2.3.4"]},
            }
        }

        merged = merge_results("example.com", results, deduplicate=True)

        assert "ips" in merged["data"]
        if "values" in merged["data"]["ips"]:
            assert len(merged["data"]["ips"]["values"]) == 1

    def test_merge_without_deduplication(self):
        """Test merge_results without deduplication."""
        results = {
            "provider1": {
                "success": True,
                "data": {"ips": ["1.2.3.4", "1.2.3.4"]},
            }
        }

        merged = merge_results("example.com", results, deduplicate=False)

        assert merged["target"] == "example.com"
        assert merged["summary"]["success"]

    def test_merge_empty_results(self):
        """Test merge with no provider results."""
        merged = merge_results("example.com", {})

        assert merged["target"] == "example.com"
        assert merged["summary"]["total_providers"] == 0
        assert merged["summary"]["success"]
