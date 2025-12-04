from pathlib import Path
from typing import Any, Optional, cast

# Import `whois` lazily inside run() to avoid import-time failures in
# environments where the package isn't installed (tests may monkeypatch the
# module at runtime). Provide a lightweight placeholder object that exposes a
# `.whois` attribute so test monkeypatching can target it without triggering
# import-time errors.
def _missing_whois(domain: str):
    raise RuntimeError("whois functionality not available in this environment")

class _WhoisPlaceholder:
    whois = staticmethod(_missing_whois)

# Start as None so we attempt a lazy import of a real whois implementation
# at runtime; tests can still monkeypatch `_pywhois` if needed.
_pywhois = None

from core.logger import get_logger
from core.module import BaseModule
from core.output import print_json, save_output, standard_response

logger = get_logger("whois_lookup")


class WhoisModule(BaseModule):
    name = "whois_lookup"
    description = "Performs WHOIS lookup for domains"
    author = "DarkReconX"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def run(self, domain: str, use_tor: Optional[bool] = None, output: Optional[str] = None):
        try:
            # Import whois lazily
            if _pywhois is None:
                try:
                    import whois as _imported_whois

                    # Ensure there is a callable attribute `.whois` for compatibility
                    if not hasattr(_imported_whois, "whois") and hasattr(_imported_whois, "query"):
                        _imported_whois.whois = _imported_whois.query  # type: ignore

                    # bind to module-level name
                    globals() ["_pywhois"] = _imported_whois
                except Exception as ie:
                    # if whois isn't available, raise to be caught below
                    raise RuntimeError("whois package not available") from ie

            # python-whois does DNS/network internally; callers should be aware
            w = cast(Any, _pywhois).whois(domain)
            result = {
                "domain": domain,
                "registrar": getattr(w, "registrar", None),
                "creation_date": str(getattr(w, "creation_date", None)),
                "expiration_date": str(getattr(w, "expiration_date", None)),
                "name_servers": getattr(w, "name_servers", None),
            }
            # save to results folder if requested
            if output:
                p = Path(output)
            else:
                p = Path(__file__).resolve().parents[2] / "results" / f"whois_{domain}.json"
            try:
                save_output(str(p), result)
            except Exception:
                # best-effort save; don't fail the module if saving isn't possible
                logger.debug("Failed to save whois result to %s", p)

            # Return structured result for CLI renderer or downstream consumers
            return result
        except Exception as e:
            logger.error(f"WHOIS lookup failed for {domain}: {e}")
            return {"success": False, "error": str(e)}

    def run_structured(self, domain: str, use_tor: Optional[bool] = None, output: Optional[str] = None) -> dict:
        """Return a structured record suitable for the renderer/CLI.

        This wrapper keeps the original `run` signature but normalizes the
        return shape to include a `target` and `type` so the renderer can
        display it consistently with other modules.
        """
        res = self.run(domain, use_tor=use_tor, output=output)
        if isinstance(res, dict) and res.get("success") is False:
            return {"target": domain, "type": "whois", "whois": {}, "error": res.get("error")}

        return {"target": domain, "type": "whois", "whois": res}
