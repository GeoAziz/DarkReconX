## Day 20 — Stabilization & Polishing

This document summarizes the stabilization changes applied on Day 20. The goal was to harden runtime behavior, normalize outputs, and improve CLI ergonomics to prepare the codebase for future feature work.

What changed
- Standardized module response shape via `core.output.standard_response()` — modules and CLI commands now produce:
  - Success: `{ "module": "name", "status": "ok", "data": {...} }`
  - Error: `{ "module": "name", "status": "error", "message": "..." }`
- Added API key helper `core.keys.check_api_key()` to check environment keys and provide a friendly skip message.
- Added profiles loader `core.profiles` and an example `config/profiles.yml` with `quick`, `full`, and `privacy` presets.
- CLI improvements in `cli/main.py`:
  - Global `--verbose` (already present) and new `--quiet / -q` flag to reduce output.
  - New `profiles` command to list available scan profiles.
  - `run` command now wraps results with the standardized response for consistent output formatting.
- Module discovery already exists at `core.loader.discover_modules()` and is used by `cli/main.py` `list` command.

Developer notes
- Profiles can be extended in `config/profiles.yml` or by adding a `profiles.yaml` at repo root.
- Providers that require API keys (e.g. VirusTotal) will be skipped if the corresponding env var is absent — avoid crashes during development.
- `core/output.py` provides `print_json`, `print_table`, and `save_output` helpers for convenient export and display.

Next steps
- Continue normalizing module internals to always return the standardized response shape (where practical).
- Add tests that assert standardized outputs for a few core modules.
- Consider creating a top-level package structure (`darkreconx/`) in a future refactor — deferred to day 21+.
