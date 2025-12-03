██████╗  █████╗ ██████╗ ██╗  ██╗██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔══██╗██╔════╝██╔════╝ ██╔══██╗████╗  ██║
██████╔╝███████║██████╔╝█████╔╝ ██║  ██║█████╗  ██║  ███╗██████╔╝██╔██╗ ██║
██╔═══╝ ██╔══██║██╔═══╝ ██╔═██╗ ██║  ██║██╔══╝  ██║   ██║██╔══██╗██║╚██╗██║
██║     ██║  ██║██║     ██║  ██╗██████╔╝███████╗╚██████╔╝██║  ██║██║ ╚████║
╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
															 DarkReconX Framework

[![CI Pipeline](https://github.com/GeoAziz/DarkReconX/actions/workflows/ci.yml/badge.svg)](https://github.com/GeoAziz/DarkReconX/actions)
[![Smoke Tests](https://github.com/GeoAziz/DarkReconX/actions/workflows/smoke.yml/badge.svg)](https://github.com/GeoAziz/DarkReconX/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

DarkReconX is a fully modular cyber-recon framework designed for hands-on
cybersecurity learning and professional OSINT research.

The toolkit integrates:

- Tor-routed anonymous reconnaissance
- Dark Web marketplace & forum scanners
- Open-source intelligence (OSINT) modules
- Threat intelligence utilities
- Plug-and-play module architecture

The project is built around an 8-week roadmap covering HTTP engine
development, Tor integration, automated recon tools, darkweb intelligence
scrapers, malware OSINT modules, and API integrations.

Designed for students, researchers, ethical hackers, and cyber analysts who
want real-world, hands-on, practical cybersecurity tooling experience.

License recommendation
----------------------

Use the MIT License. It allows others to use and contribute freely while
keeping a permissive and standard legal footing for OSINT frameworks.

Quick start (PowerShell)
------------------------

Create virtual environment and activate

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell
```

Install dependencies

```powershell
pip install -r requirements.txt
```

Run CLI launcher

```powershell
python .\cli\main.py
```

Notes
-----
- If dependencies are not installed the CLI will show import errors — run
	`pip install -r requirements.txt` first.
- Add your GitHub remote and push when ready.

Development & Testing
---------------------

### Setup for Contributors

Clone the repository and set up the development environment:

```powershell
git clone https://github.com/GeoAziz/DarkReconX.git
cd DarkReconX
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell
pip install -e ".[dev]"        # Install with dev dependencies
```

### Running Tests

Run the full test suite:

```powershell
pytest -q
```

Run tests with coverage report:

```powershell
pytest --cov=core --cov=modules --cov=config --cov-report=html --cov-report=term-missing -q
```

Coverage report will be generated in `htmlcov/` (open `htmlcov/index.html` in a browser).

### Code Quality Checks

Check code style and linting:

```powershell
black --check .           # Check Black formatting
isort --check-only .      # Check import sorting
flake8 .                  # Lint with flake8
```

Auto-format and fix issues:

```powershell
black .                   # Auto-format with Black
isort .                   # Auto-sort imports
```

### CI/CD Pipeline

GitHub Actions automatically runs on every push and PR:

1. **Lint stage**: Black, isort, flake8, mypy validation
2. **Test stage**: Full pytest suite with coverage reporting (80%+ core target)
3. **Smoke stage**: CLI import regression detection
4. **Integration stage**: Optional API integration tests (gated by main branch + secrets)

See `.github/workflows/` for workflow definitions.

### Pre-commit Hooks

Install pre-commit hooks to validate code before commits:

```powershell
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

See `.pre-commit-config.yaml` for hook configuration.

For more detailed contribution guidelines, see `CONTRIBUTING.md` and `CONTRIBUTING_MODULES.md`.


API keys & .env
----------------

DarkReconX supports optional third-party API integrations (for example
VirusTotal) to enrich findings. For local development you can store
credentials in a top-level `.env` file (this repo already includes
`.env` in `.gitignore` to avoid accidental commits).

Environment variables supported by the framework:
- `VT_API_KEY` — VirusTotal v3 API key used by the subfinder enrichment helper.
- `TOR_PASSWORD`, `TOR_CONTROL_PORT`, `TOR_SOCKS_PORT` — override Tor config.

The `config` loader will automatically read `.env` (if present) and overlay
these values, so modules can pick up API keys from `get_config()` or from
`os.environ`.

Recommended reconnaissance stack
--------------------------------

Based on current priorities, the following stack is recommended to replace
SecurityTrails and form the baseline enrichment pipeline:

- SUBDOMAINS:
	- subfinder (local DNS/wordlist)
	- crt.sh (certificate-to-subdomain lookups)
	- VirusTotal (API-driven domain/subdomain intelligence)

- DNS + HISTORICAL DNS:
	- DNSDB Scout (free pDNS)
	- VirusTotal (DNS records)
	- crt.sh (cert → DNS)

- WHOIS:
	- whoisxml (free tier)
	- VirusTotal (WHOIS via VT)

- IP INTELLIGENCE:
	- ipinfo.io (free tier)
	- VirusTotal (IP relations)

- INFRASTRUCTURE ENUMERATION:
	- httpx, naabu, dnsx
	- crt.sh
	- VirusTotal graphs

See `CONTRIBUTING_MODULES.md` for how to add or wire these integrations into
modules safely and how to mock them for networkless CI.
