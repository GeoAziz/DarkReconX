"""core.result_merger

Unified result merging and deduplication logic.

Combines normalized provider outputs into a single structured JSON result.
"""

from typing import Any, Dict, List, Set

from core.logger import get_logger

logger = get_logger("result_merger")


class ResultMerger:
    """Merge provider results into unified output."""

    @staticmethod
    def merge(
        target: str,
        provider_results: Dict[str, Dict[str, Any]],
        include_raw: bool = False,
    ) -> Dict[str, Any]:
        """Merge multiple provider results into unified schema.

        Args:
            target: Original scan target
            provider_results: Dict mapping provider_name -> provider_result
            include_raw: Include raw provider responses

        Returns:
            Merged result with standardized schema.
        """
        merged = {
            "target": target,
            "summary": {
                "total_providers": len(provider_results),
                "successful_providers": 0,
                "failed_providers": 0,
            },
            "data": {},
            "providers": {},
            "errors": {},
        }

        # Process each provider (accept both standardized envelope and legacy shapes)
        for provider_name, result in provider_results.items():
            if not isinstance(result, dict):
                continue

            # If the provider returned a standardized envelope, extract fields
            if "status" in result:
                success = result.get("status") == "ok"
                execution_time = result.get("execution_time_seconds", 0)
                cached = result.get("cached", False)
                data = result.get("data")
                error = result.get("message") or result.get("error")
            else:
                # Legacy shape
                success = result.get("success", False)
                execution_time = result.get("execution_time_seconds", 0)
                cached = result.get("cached", False)
                data = result.get("data")
                error = result.get("error")

            provider_entry = {
                "success": success,
                "execution_time_seconds": execution_time,
                "cached": cached,
            }

            if success:
                merged["summary"]["successful_providers"] += 1

                # Extract provider data
                if data is not None:
                    provider_entry["data"] = data
                    # Merge field-level data into unified sections
                    ResultMerger._merge_fields(merged["data"], data, provider_name)
            else:
                merged["summary"]["failed_providers"] += 1
                merged["errors"][provider_name] = error or "Unknown error"

            # Store per-provider metadata
            if include_raw and "raw" in result:
                provider_entry["raw"] = result["raw"]

            merged["providers"][provider_name] = provider_entry

        merged["summary"]["success"] = merged["summary"]["failed_providers"] == 0

        return merged

    @staticmethod
    def _merge_fields(unified: Dict[str, Any], provider_data: Dict[str, Any], provider_name: str) -> None:
        """Merge provider data fields into unified sections.

        Args:
            unified: Unified data dict to merge into
            provider_data: Provider-specific data
            provider_name: Name of provider for tagging
        """
        # Deduplicate and tag common fields
        for key, value in provider_data.items():
            if key == "success" or key == "error":
                continue

            if key not in unified:
                unified[key] = {}

            # Initialize field structure if needed
            if not isinstance(unified[key], dict):
                unified[key] = {}

            if "sources" not in unified[key]:
                unified[key]["sources"] = {}

            # Add value with provider source tag
            if isinstance(value, list):
                if "values" not in unified[key]:
                    unified[key]["values"] = []
                # Deduplicate list items
                for item in value:
                    if item not in unified[key]["values"]:
                        unified[key]["values"].append(item)
                unified[key]["sources"][provider_name] = len(value)
            elif isinstance(value, dict):
                if "details" not in unified[key]:
                    unified[key]["details"] = {}
                unified[key]["details"][provider_name] = value
            else:
                if "values" not in unified[key]:
                    unified[key]["values"] = []
                if value not in unified[key]["values"]:
                    unified[key]["values"].append(value)
                unified[key]["sources"][provider_name] = True


class ResultDeduplicator:
    """Deduplicate results across providers."""

    @staticmethod
    def deduplicate_ips(ip_list: List[str]) -> List[str]:
        """Remove duplicate IPs while preserving order."""
        seen: Set[str] = set()
        result = []
        for ip in ip_list:
            if ip not in seen:
                seen.add(ip)
                result.append(ip)
        return result

    @staticmethod
    def deduplicate_domains(domain_list: List[str]) -> List[str]:
        """Remove duplicate domains (case-insensitive) while preserving order."""
        seen: Set[str] = set()
        result = []
        for domain in domain_list:
            norm = domain.lower()
            if norm not in seen:
                seen.add(norm)
                result.append(domain)
        return result

    @staticmethod
    def deduplicate_dns_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate DNS records by (type, value)."""
        seen: Set[tuple] = set()
        result = []
        for record in records:
            key = (record.get("type", "").upper(), record.get("value", "").lower())
            if key not in seen:
                seen.add(key)
                result.append(record)
        return result

    @staticmethod
    def merge_metadata(metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge metadata dicts, preferring non-None values."""
        merged = {}
        for meta in metadata_list:
            if isinstance(meta, dict):
                for key, value in meta.items():
                    # Prefer non-None values, but allow None to override
                    if key not in merged or value is not None:
                        merged[key] = value
        return merged


def merge_results(
    target: str,
    provider_results: Dict[str, Dict[str, Any]],
    deduplicate: bool = True,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """Convenience function to merge provider results.

    Args:
        target: Scan target
        provider_results: Dict of provider_name -> result
        deduplicate: Apply deduplication to common fields
        include_raw: Include raw provider responses

    Returns:
        Merged result dict.
    """
    merged = ResultMerger.merge(target, provider_results, include_raw=include_raw)

    if deduplicate:
        # Deduplicate common fields
        if "ips" in merged["data"] and "values" in merged["data"]["ips"]:
            merged["data"]["ips"]["values"] = ResultDeduplicator.deduplicate_ips(merged["data"]["ips"]["values"])

        if "domains" in merged["data"] and "values" in merged["data"]["domains"]:
            merged["data"]["domains"]["values"] = ResultDeduplicator.deduplicate_domains(merged["data"]["domains"]["values"])

        if "dns_records" in merged["data"] and "values" in merged["data"]["dns_records"]:
            merged["data"]["dns_records"]["values"] = ResultDeduplicator.deduplicate_dns_records(
                merged["data"]["dns_records"]["values"]
            )

    logger.info(
        f"Merged results for {target}: {merged['summary']['successful_providers']} "
        f"successful, {merged['summary']['failed_providers']} failed"
    )

    return merged
