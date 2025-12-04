# DarkReconX TUI - Complete Guide

## Overview

The DarkReconX TUI is a fully interactive terminal user interface for running OSINT scans with real-time feedback, error tracking, and flexible result viewing. Built with **Textual** and **Rich**, it provides a modern, intuitive experience for security researchers and penetration testers.

## Installation & Dependencies

### Prerequisites

- Python 3.8+
- pip

### Install Required Packages

```bash
pip install textual rich
```

### Recommended Additional Packages

For CSV export support (included in most Python installations):

```bash
pip install python-dateutil
```

## Quick Start

### Launch the TUI

From the repository root:

```bash
python tui.py
```

Or via the CLI:

```bash
python -m cli.main tui
```

### Basic Workflow

1. **Select Modules** (left panel):
   - Search modules by name or description using the search field
   - Click or spacebar to toggle module selection

2. **Choose Profile** (left panel):
   - Quick: Fast scan (~15 sec)
   - Full: Complete scan with all modules (~2-5 min)
   - Privacy: Privacy-focused Tor/DNS checks (~30 sec)
   - Developer: GitHub, email, SSL checks (~1 min)

3. **Enter Target** (left panel):
   - **Domain**: `example.com`, `subdomain.example.org`
   - **IP Address**: `192.168.1.1`, `8.8.8.8`
   - **Email**: `user@example.com`
   - Validation feedback shows in real-time (green=valid, red=invalid, yellow=pending)

4. **Run Scan** (left panel):
   - Press `R` or click "Run Scan" button
   - Progress bar updates as modules complete
   - Results stream into the right panel

5. **Review Results & Errors** (right panel):
   - Toggle between JSON (full data) and Table views with `T`
   - Press `E` to view errors and failure messages with suggestions
   - Check logs (bottom right) for detailed progress messages

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `R` | Run Scan | Start scan with selected settings |
| `M` | Toggle Modules | Show/hide modules list |
| `P` | Toggle Profiles | Show/hide profile selector |
| `L` | Toggle Logs | Show/hide logs panel |
| `E` | Toggle Errors | Show/hide errors panel (failures & suggestions) |
| `T` | Toggle View | Switch between JSON and Table view modes |
| `C` | Clear Results | Clear all current results |
| `Ctrl+E` | Export Results | Export to JSON and CSV files |
| `Ctrl+T` | Toggle Theme | Switch between Dark and Light themes |
| `H` | Show Help | Display this help menu in logs |
| `Q` | Quit | Exit the TUI |

## Features

### 1. Module Selection & Discovery

- **Searchable Module List**: Type in the search field to filter modules by name or description
- **Module Descriptions**: Hover over or view descriptions for each module to understand its purpose
- **Multi-Select**: Check any combination of modules to run in a single scan

### 2. Profile-Based Scanning

Each profile targets specific use cases:

| Profile | Modules | Use Case | Time |
|---------|---------|----------|------|
| Quick | DNS, SSL, WHOIS, Tor | Get fast overview | ~15s |
| Full | All available modules | Complete OSINT | ~2-5m |
| Privacy | Tor check, DNS | Privacy-focused analysis | ~30s |
| Developer | GitHub, Email, SSL | Developer footprint | ~1m |

### 3. Target Validation

The TUI validates targets before scanning:

- **Domain**: `example.com`, `sub.example.org`
- **IP Address**: `192.168.0.1` through `255.255.255.255`
- **Email**: `user@domain.com` format

Validation feedback appears in real-time with color coding:
- 🟢 **Green**: Valid target
- 🔴 **Red**: Invalid format
- 🟡 **Yellow**: Awaiting input

### 4. Results Management

#### JSON View (Default)
- Full structured data for each module result
- Syntax-highlighted Pretty JSON display
- Ideal for integration and data processing

#### Table View
- Summary view of key-value pairs
- Easier scanning of large datasets
- Press `T` to toggle

#### Collapsible Results
- Click module results to expand/collapse
- Reduces visual clutter during long scans

### 5. Error Handling & Diagnostics

Press `E` to open the Errors Panel:

- **Failures Highlighted**: All module errors appear with timestamps
- **Smart Suggestions**: The TUI suggests common fixes:
  - "Check your internet connection" for timeouts
  - "Configure API keys in core/keys.py" for auth errors
  - "Verify target format" for invalid input errors
- **Error Tracking**: Errors persist through scan for easy review

### 6. Live Progress & Status

- **Progress Bar**: Visual representation of scan completion (0-100%)
- **Module Count**: Real-time count of completed modules
- **Status Bar**: Bottom status bar shows current scan state:
  - "Ready" when idle
  - "Running scan with X modules..." during execution
  - "Scan complete: N errors, M successful" when done

### 7. Export Functionality

Press `Ctrl+E` to export results:

**JSON Export**:
- Full structured format with all nested data
- Filename: `scan_results_YYYYMMDD_HHMMSS.json`
- Compatible with downstream tools

**CSV Export**:
- Flattened key-value format
- Nested objects converted to JSON strings
- Filename: `scan_results_YYYYMMDD_HHMMSS.csv`
- Excel/Google Sheets friendly

Files are saved in the current working directory.

### 8. Theme Toggle

Press `Ctrl+T` to toggle between:

- **Dark Theme** (default): Black background, colored accents
- **Light Theme**: Light background, adjusted colors
- **Persistence**: Theme preference is saved (~/.darkreconx_theme) and restored on next launch

## View Modes

### JSON Mode
```
{
  "module": "github_osint",
  "status": "ok",
  "data": {
    "username": "john_doe",
    "repos": [...],
    ...
  }
}
```

### Table Mode
```
Key          | Value
-------------|-------
module       | github_osint
status       | ok
username     | john_doe
repo_count   | 15
```

## Status Bar Information

The status bar at the bottom displays:

- **Timestamp**: Current time (HH:MM:SS)
- **Current Status**: Idle, Running, Error states
- **Module Progress**: "Running: github_osint completed"
- **Errors**: "Error in email_osint" during failures

## Common Use Cases

### 1. Quick Domain Reconnaissance

```
1. Select "Quick" profile
2. Enter: example.com
3. Press R
```

Gathers WHOIS, DNS, and basic SSL info in ~15 seconds.

### 2. Comprehensive OSINT

```
1. Select "Full" profile
2. Select specific modules (if desired)
3. Enter: target.com
4. Press R
5. Export results with Ctrl+E
```

Complete footprint including all available modules.

### 3. API Key Testing

```
1. Select single module (e.g., VirusTotal, Shodan)
2. Enter target
3. Press R
4. Check Errors panel (E) for auth errors
5. Configure keys in core/keys.py
6. Retry
```

## Troubleshooting

### "Module not found" Error

**Cause**: Module not in modules/ directory or discovery failed
**Solution**: 
- Check core/loader.py for discovery issues
- Restart TUI with `python tui.py`

### Target Validation Fails

**Cause**: Invalid format or malformed input
**Solution**:
- Ensure domain contains a dot (example.com)
- IP must be 4 octets (0-255)
- Email must have @ and domain

### API Key Errors

**Cause**: Missing or invalid API keys
**Solution**:
- Configure keys in `core/keys.py`
- Check PROFILE configuration in `config/profiles.yml`
- Restart TUI to reload config

### Results Not Showing

**Cause**: Provider failed or scan incomplete
**Solution**:
- Check Errors panel (E)
- Review logs (toggle L if hidden)
- Verify internet connection
- Increase timeout in orchestrator settings

### Theme Not Persisting

**Cause**: Write permission issue on ~/.darkreconx_theme
**Solution**:
- Check home directory permissions
- Theme will work during session even if persistence fails

## Advanced Configuration

### Custom Profiles

Edit `config/profiles.yml` to create custom scan profiles:

```yaml
my_profile:
  modules:
    - github_osint
    - email_osint
    - ssl_info
  timeout: 60
```

Then select in TUI Profile dropdown.

### Module-Specific Settings

Configure in `core/keys.py` or module-specific config files:

```python
API_KEYS = {
    "shodan": "YOUR_SHODAN_KEY",
    "virustotal": "YOUR_VT_KEY",
}
```

### Log Levels

Control logging verbosity in `core/logger.py` (future enhancement).

## Known Limitations

1. **Per-Module Progress**: Shows only module completion, not internal progress
2. **Table View**: Limited to top-level keys (nested data shown as JSON strings)
3. **Terminal Size**: Recommended minimum 120x40 characters for full UI
4. **ASCII Art**: Symbols (✓, ✗) may not render on all terminals (falls back to text)

## Performance Tips

- **Quick Scans**: Use "Quick" profile for fast turnaround
- **Large Result Sets**: Export to CSV for spreadsheet analysis
- **Long Scans**: Use "Privacy" profile if network is slow
- **Error-Heavy Scans**: Enable Errors panel early to catch issues

## Support & Documentation

- **Help**: Press `H` in TUI for shortcuts
- **Modules Guide**: See docs/modules.md
- **CLI Guide**: See cli/main.py --help
- **Issues**: Report on GitHub (GeoAziz/DarkReconX)

## Next Steps

- Try the Quick profile with `example.com`
- Explore module descriptions using the search field
- Export a scan result with Ctrl+E
- Toggle themes with Ctrl+T to find your preference
- Press H anytime for full help

Happy scanning! 🚀
