from typing import Any, Dict, List, Optional
import socket
import ssl
from datetime import datetime

from core.module import BaseModule
from core.output import standard_response, save_output


class SSLInfoModule(BaseModule):
    name = "ssl_info"
    description = "Fetch public SSL/TLS certificate metadata for a host"

    def run(self, host: str, port: int = 443, output: Optional[str] = None) -> Dict[str, Any]:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()

            # ensure cert is a dict to avoid attribute errors if getpeercert() returns None
            if cert is None:
                cert = {}

            # cert is a dict; parse fields
            subject = cert.get("subject", [])
            common_name = None
            for part in subject:
                for k, v in part:
                    if k == "commonName":
                        common_name = v

            issuer = None
            issuer_parts = cert.get("issuer", [])
            for part in issuer_parts:
                for k, v in part:
                    if k == "organizationName":
                        issuer = v

            not_before = cert.get("notBefore")
            not_after = cert.get("notAfter")

            # SANs
            san = []
            for item in cert.get("subjectAltName", []):
                # item is expected to be a (type, value) tuple; guard against malformed entries
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                typ, val = item
                if isinstance(typ, str) and typ.lower() in ("dns", "subjectaltname"):
                    san.append(val)

            # compute days left
            days_left = None
            # ensure not_after is a string before passing to strptime (type-checker-safe)
            if isinstance(not_after, str) and not_after:
                try:
                    # Example format: 'Nov 15 12:00:00 2025 GMT'
                    dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_left = (dt - datetime.utcnow()).days
                except Exception:
                    days_left = None
            else:
                # If not_after isn't a string (malformed cert), leave days_left as None
                days_left = None

            data: Dict[str, Any] = {
                "common_name": common_name or host,
                "issuer": issuer,
                "valid_from": not_before,
                "valid_to": not_after,
                "days_left": days_left,
                "san": san,
            }

            if output:
                save_output(output, data)

            return standard_response("ssl_info", data=data)
        except Exception as e:
            return standard_response("ssl_info", error=str(e))
