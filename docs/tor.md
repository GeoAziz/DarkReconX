# Tor Integration — DarkReconX

This document describes how DarkReconX uses Tor and how to test it locally.

Prerequisites
- Install Tor (system package or Tor Browser).
- Start Tor so that a SOCKS5 proxy is available on `127.0.0.1:9050`.
- (Optional) Configure Tor control port (9051) and set a password if you want
  programmatic NEWNYM (IP rotation).

Python requirements
- requests
- pysocks
- stem (optional, for NEWNYM)

Quick usage

- Non-Tor HTTP example (direct):

  ```python
  from core.http_client import HTTPClient
  c = HTTPClient(use_tor=False)
  print(c.get("http://httpbin.org/ip"))
  ```

- Tor routed example:

  ```python
  from core.http_client import HTTPClient
  c = HTTPClient(use_tor=True)
  print(c.get("http://httpbin.org/ip"))
  ```

Notes
- If Tor is not running the Tor-routed example will return `None` and print
  a warning. Make sure Tor is running before relying on Tor connectivity.

Programmatic IP rotation (NEWNYM)

If you want to change Tor circuits you can use the Stem helper in
`core/tor_client.py::new_tor_identity`. You must configure Tor's control port
and authenticate. A common approach:

1. In your `torrc`, enable control port and set a hashed password.
2. Export the password as an environment variable `TOR_CONTROL_PASSWORD` or
   pass it to `new_tor_identity(password=...)`.

Security and safety
- Only use Tor and recon tools for lawful, ethical research.
- Many onion services and dark-web resources can be illegal — avoid
  interacting with content that breaks the law.

Troubleshooting
- If you see proxy/socket errors, verify Tor is running and reachable at
  `127.0.0.1:9050`.
- For control port issues, ensure `controlport 9051` is enabled in `torrc` and
  that the password is correct.
