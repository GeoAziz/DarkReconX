from typing import Any, Dict


def compute_confidence(sources: Dict[str, Any]) -> float:
    """Compute a simple confidence score based on available sources.

    confidence = (sources_successful / sources_total) + validation_bonus - conflict_penalty
    Returns a float between 0 and 1+. This is intentionally simple and
    intended to be improved later.
    """
    if not sources:
        return 0.0

    total = len(sources)
    successful = 0
    for k, v in sources.items():
        if v:
            successful += 1

    sources_successful = successful
    sources_total = total if total > 0 else 1

    # validation bonus: if local cache or local_dns present
    validation_bonus = 0.1 if ("cache" in sources or "local_dns" in sources) else 0.0

    # conflict penalty: naive check for conflicting registrar data etc.
    conflict_penalty = 0.0

    confidence = (sources_successful / sources_total) + validation_bonus - conflict_penalty
    # clamp between 0 and 1.0 for now
    if confidence < 0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0
    return round(confidence, 2)


def fuse_domain(domain: str, sources: Dict[str, Any]) -> Dict[str, Any]:
    return {"domain": domain, "sources": sources, "confidence": compute_confidence(sources)}
