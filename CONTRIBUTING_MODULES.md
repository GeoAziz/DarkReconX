CONTRIBUTING: Modules for DarkReconX

This guide explains how to write and test modules for DarkReconX.

Why follow this guide?
- Ensures consistency across modules.
- Makes modules plug-and-play with the CLI and loader.
- Prevents accidental network activity during import or CI.

Module contract (BaseModule)
- Location: `core/module.py` defines `BaseModule`.
- Required:
  - class must inherit from `BaseModule`.
  - provide `name` (string) and `description` (string) class attributes.
  - implement `run(self, *args, **kwargs)` which performs the module's work.
- Optional:
  - `author` attribute (defaults to DarkReconX).
  - Accept framework kwargs in `__init__(self, **kwargs)` like `use_tor`, `verbose`.

Best practices
- Do NOT perform network I/O or heavy work in `__init__`.
  - `__init__` should only parse/store configuration and options.
- Do all network access and long-running work inside `run()`.
- Use framework helpers for output and logging:
  - `from core.output import print_json, print_table, save_output, print_header`
  - `from core.logger import get_logger` to obtain a logger for your module.
- Keep `run()` return values serializable (dict, list) so the CLI can save or format results.

Example minimal module

```python
from core.module import BaseModule
from core.output import print_json

class MyModule(BaseModule):
    name = "my_module"
    description = "An example module"

    def run(self, text: str = "hello"):
        data = {"result": text}
        print_json(data)
        return data
```

How module discovery works
- The loader searches `modules/` for either:
  - `modules/<name>.py` (single-file module), or
  - `modules/<name>/scanner.py` (package-style module).
- It imports the candidate module and looks for classes that subclass `BaseModule`.
- To ensure your module is discovered, name it and expose a subclass of `BaseModule`.

Testing a module locally
- To test discoverability and run your module locally:
  - `python -c "from core.loader import discover_modules; print(discover_modules())"`
  - `python -c "from core.loader import load_module; m=load_module('my_module'); print(m.run())"`

Tor / networking guidance
- Modules that need Tor should accept a `use_tor` option and use the framework's
  HTTPClient which respects Tor when `use_tor=True`.
- Do not assume Tor is available; check `core.tor_client.is_tor_available()` if you need to inform the user.

API keys and recommended stack
- Store API keys in environment variables or a top-level `.env` file (project
  `config.loader` will read `.env` automatically). Do NOT hardcode keys in
  module source or commit them to the repository.
- The framework looks for commonly used variables such as `VT_API_KEY` (VirusTotal).
- Prefer using `core.cache` when calling external APIs to reduce rate-limit
  pressure during development and CI runs.

Recommended providers (replace SecurityTrails)
- VirusTotal (domains, DNS, WHOIS, IP relations)
- DNSDB Scout (passive DNS)
- crt.sh (certificate scraping → domains)
- whoisxml (WHOIS lookups)
- ipinfo.io (IP intelligence)

When adding new API-backed modules:
- Provide a non-networking fallback or mock for unit tests (see existing tests).
- Honor config and env-based API keys; prefer `get_config().config.get('virustotal', {}).get('api_key')`.
- Cache responses via `core.cache.get_cached` / `core.cache.set_cached`.

Output rules
- Prefer returning structured data from `run()` (a dict or list). The CLI will print and/or save results.
- Use `print_json()` for machine-friendly output and `print_table()` when tabular view helps.
- Use `save_output(path, data)` for persistent storage (JSON by default).

CI and import-time rules
- Avoid external network calls during import time. CI networkless smoke checks import modules and run the `template` module. Failures here usually mean your module does network work at import time.

Style / contribution notes
- Keep public APIs stable and document new module behavior in the module docstring.
- Add unit tests under `tests/` and prefer mocking network calls.

Thanks for contributing!
