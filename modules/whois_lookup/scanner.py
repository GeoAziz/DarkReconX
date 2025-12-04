from pathlib import Path
from typing import Any, Optional

import whois as _pywhois

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
            # python-whois does DNS/network internally; callers should be aware
            w = _pywhois.whois(domain)
            result = {
                "domain": domain,
                "registrar": getattr(w, "registrar", None),
                "creation_date": str(getattr(w, "creation_date", None)),
                "expiration_date": str(getattr(w, "expiration_date", None)),
                "name_servers": getattr(w, "name_servers", None),
            }
            # print to console
            print_json(result)
            # save to results folder if requested
            if output:
                p = Path(output)
            else:
                p = Path(__file__).resolve().parents[2] / "results" / f"whois_{domain}.json"
            save_output(str(p), result)
            return standard_response("whois_lookup", data=result)
        except Exception as e:
            logger.error(f"WHOIS lookup failed for {domain}: {e}")
            return standard_response("whois_lookup", error=str(e))
