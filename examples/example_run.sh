#!/usr/bin/env bash
# Example run script for DarkReconX — safe demo on a controlled target
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Create a small targets file for the demo
mkdir -p examples/data results/reports
echo "example.com" > examples/data/sample_targets.txt

# Run ASR module on safe target with conservative port list
echo "[*] Running DarkReconX ASR demo on example.com..."
python -m cli.main asr --targets examples/data/sample_targets.txt --top-ports 20 --output results/asr_output.json || {
  echo "[!] ASR run encountered an issue; continuing with demo..."
}

# Generate a report from sample data
echo "[*] Generating markdown report..."
python -c "
import json
import os
from reports.generator import generate

# Create sample unified result
sample_data = {
  'target': 'example.com',
  'scan_time': '2025-12-03T00:00:00Z',
  'risk': {'score': 3, 'reasons': ['open_port:22', 'http_server_banner']},
  'assets': ['example.com', 'www.example.com']
}

# Generate report
report_path = generate('example.com', sample_data, format='md')
print(f'[+] Report generated: {report_path}')
" || {
  echo "[!] Report generation skipped (sample run)"
}

echo "[+] Demo complete — see results/ and results/reports/"
