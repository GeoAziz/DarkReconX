from typing import Any, Dict, List, Optional
import re

import dns.resolver

from core.module import BaseModule
from core.output import standard_response, save_output


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailOsintModule(BaseModule):
    name = "email_osint"
    description = "Passive email and domain intelligence (MX/SPF/DMARC/DKIM checks)"

    def run(self, email: str, output: Optional[str] = None) -> Dict[str, Any]:
        try:
            valid_format = bool(EMAIL_RE.match(email))
            domain = email.split("@", 1)[1] if valid_format else None

            mx_records: List[str] = []
            spf: Optional[str] = None
            dmarc: Optional[str] = None
            dkim: Optional[str] = None

            if domain:
                # MX
                try:
                    answers = dns.resolver.resolve(domain, "MX")
                    rrset = getattr(answers, "rrset", None)
                    if rrset:
                        for r in rrset:
                            # r.exchange is a Name object
                            mx_records.append(str(getattr(r, "exchange", r)).rstrip("."))
                except Exception:
                    mx_records = []

                # TXT -> SPF
                try:
                    answers = dns.resolver.resolve(domain, "TXT")
                    rrset = getattr(answers, "rrset", None)
                    if rrset:
                        for t in rrset:
                            if hasattr(t, "strings"):
                                # dnspython returns bytes in .strings
                                s = b"".join(t.strings).decode(errors="ignore")
                            else:
                                s = str(t)
                            if s.startswith("v=spf1"):
                                spf = s
                                break
                except Exception:
                    spf = None
                # DMARC at _dmarc.domain
                try:
                    d = f"_dmarc.{domain}"
                    answers = dns.resolver.resolve(d, "TXT")
                    rrset = getattr(answers, "rrset", None)
                    if rrset:
                        for t in rrset:
                            if hasattr(t, "strings"):
                                s = b"".join(t.strings).decode(errors="ignore")
                            else:
                                s = str(t)
                            if s.lower().startswith("v=dmarc1"):
                                dmarc = s
                                break
                except Exception:
                    dmarc = None

                # DKIM: check for a common selector existence (default)
                try:
                    selector = "default._domainkey." + domain
                    txt = dns.resolver.resolve(selector, "TXT")
                    if txt:
                        dkim = selector
                except Exception:
                    dkim = None

            result = {
                "valid_format": valid_format,
                "domain": domain,
                "mx_records": mx_records,
                "spf": spf,
                "dmarc": dmarc,
                "dkim": dkim,
            }

            if output:
                save_output(output, result)

            return standard_response("email_osint", data=result)
        except Exception as e:
            return standard_response("email_osint", error=str(e))
