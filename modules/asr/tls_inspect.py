import asyncio
import socket
import ssl
from datetime import datetime
from typing import Any, Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend


async def fetch_cert(host: str, port: int = 443, timeout: int = 5) -> Optional[Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_cert, host, port, timeout)


def _get_cert(host: str, port: int, timeout: int) -> Optional[Any]:
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            der_cert: Optional[bytes] = ssock.getpeercert(True)
            if not der_cert:
                return None
            cert = x509.load_der_x509_certificate(der_cert, default_backend())
            return cert


async def tls_inspect(host: str, port: int = 443, timeout: int = 5) -> dict:
    try:
        cert = await fetch_cert(host, port, timeout)
        if not cert:
            return {}
        issuer = cert.issuer.rfc4514_string()
        san = []
        try:
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            san = ext.value.get_values_for_type(x509.DNSName)
        except Exception:
            pass
        valid_from = cert.not_valid_before.strftime("%Y-%m-%d")
        valid_to = cert.not_valid_after.strftime("%Y-%m-%d")
        days_left = (cert.not_valid_after - datetime.utcnow()).days
        sig_alg = cert.signature_hash_algorithm.name
        weak_cipher = sig_alg in ("md5", "sha1")
        return {
            "issuer": issuer,
            "san": san,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "days_left": days_left,
            "weak_cipher": weak_cipher,
        }
    except Exception:
        return {}
