# Roadmap — DarkReconX (8-Week Plan)

## Goals
- Build a modular OSINT framework for dark web + open web recon.

## 8-Week Plan (high level)

Week 1-2: Core engine, CLI, 20 module skeletons, CI/tests scaffolding.
Week 3-4: Implement top 6 modules (onion crawler, dark market scanner, breach lookup, email recon, username recon, pastebin monitor).
Week 5-6: Add automation (selenium/Playwright), Tor integration, sandboxed malware analysis modules.
Week 7: Add API/dashboard and expand reporting, data export.
Week 8: Hardening, tests, docs, release.

## Tools mapping
- HTTP/Tor engine: `core/`
- CLI: `cli/`
- Modules: `modules/` (one per tool)
- Tests: `tests/`

## Day-by-day (sample for Week 1)
- Day 1: Project foundation, skeletons (this commit).
- Day 2: Implement CLI menu and module loader.
- Day 3: Implement HTTP client & Tor client proof-of-concept.

## Dependencies
See `requirements.txt` (requests, beautifulsoup4, selenium, httpx, rich, aiohttp, stem, dnspython, typer, pyfiglet)

## API / Data flow
- Modules call the core HTTP client.
- Results are normalized and written to module-specific reports.
- CLI orchestrates module runs; API exposes run/status.

(Expand diagrams and tasks as implementation progresses.)
