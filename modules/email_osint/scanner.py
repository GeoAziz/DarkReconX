import re
from typing import Any, Dict, Iterable, List, Optional, cast

import dns.resolver

from core.module import BaseModule
from core.output import save_output, standard_response

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
                    # dnspython may return an Answer object or expose an .rrset
                    rrset = getattr(answers, "rrset", None)
                    iterable: Iterable = rrset if rrset is not None else cast(Iterable, answers)
                    for r in iterable:
                        mx_records.append(str(getattr(r, "exchange", r)).rstrip("."))
                except Exception:
                    mx_records = []

                # TXT -> SPF
                try:
                    answers = dns.resolver.resolve(domain, "TXT")
                    found = False
                    rrset = getattr(answers, "rrset", None)
                    iterator: Iterable = rrset if rrset is not None else cast(Iterable, answers)
                    for t in iterator:
                        if hasattr(t, "strings"):
                            s = b"".join(t.strings).decode(errors="ignore")
                        else:
                            s = str(t)
                        if s.lower().startswith("v=spf1"):
                            spf = s
                            found = True
                            break
                    if not found:
                        spf = None
                except Exception:
                    spf = None
                # DMARC at _dmarc.domain
                try:
                    d = f"_dmarc.{domain}"
                    answers = dns.resolver.resolve(d, "TXT")
                    found = False
                    rrset = getattr(answers, "rrset", None)
                    iterator: Iterable = rrset if rrset is not None else cast(Iterable, answers)
                    for t in iterator:
                        if hasattr(t, "strings"):
                            s = b"".join(t.strings).decode(errors="ignore")
                        else:
                            s = str(t)
                        if s.lower().startswith("v=dmarc1"):
                            dmarc = s
                            found = True
                            break
                    if not found:
                        dmarc = None
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
